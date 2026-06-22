#include "mpi_support.h"
#include "md5.h"
#include <algorithm>
#include <chrono>
#include <cstdlib>
#include <cstring>

using namespace std;
using namespace chrono;

namespace mpi_guess
{

static uint64_t ParseUnsigned(const char *value, uint64_t fallback)
{
    char *end = nullptr;
    const unsigned long long parsed = strtoull(value, &end, 10);
    return end != value && *end == '\0' ? static_cast<uint64_t>(parsed) : fallback;
}

RuntimeOptions ParseOptions(int argc, char **argv)
{
    RuntimeOptions options;
    for (int i = 1; i < argc; i += 1)
    {
        const string arg = argv[i];
        if (arg == "--serial")
        {
            options.use_simd = false;
        }
        else if (arg == "--generate" && i + 1 < argc)
        {
            options.generate_limit = ParseUnsigned(argv[++i], options.generate_limit);
        }
        else if (arg == "--batch-guesses" && i + 1 < argc)
        {
            options.batch_guesses = max<uint64_t>(1, ParseUnsigned(argv[++i], options.batch_guesses));
        }
        else if (arg == "--batch-units" && i + 1 < argc)
        {
            options.batch_units = max(1, static_cast<int>(ParseUnsigned(argv[++i], options.batch_units)));
        }
        else if (arg == "--gen-threads" && i + 1 < argc)
        {
            options.gen_threads = max(1, static_cast<int>(ParseUnsigned(argv[++i], options.gen_threads)));
        }
    }
    return options;
}

static void AddPackSize(int count, MPI_Datatype datatype, MPI_Comm comm, int &size)
{
    int part = 0;
    MPI_Pack_size(count, datatype, comm, &part);
    size += part;
}

std::vector<char> PackWorkUnit(const WorkUnit &unit, MPI_Comm comm)
{
    int size = 0;
    AddPackSize(1, MPI_INT, comm, size);
    AddPackSize(static_cast<int>(unit.pt.content.size() * 2), MPI_INT, comm, size);
    AddPackSize(1, MPI_INT, comm, size);
    AddPackSize(1 + static_cast<int>(unit.pt.curr_indices.size()), MPI_INT, comm, size);
    AddPackSize(1 + static_cast<int>(unit.pt.max_indices.size()), MPI_INT, comm, size);
    AddPackSize(2, MPI_FLOAT, comm, size);
    AddPackSize(2, MPI_UNSIGNED_LONG_LONG, comm, size);

    vector<char> buffer(size);
    int position = 0;
    int content_count = static_cast<int>(unit.pt.content.size());
    MPI_Pack(&content_count, 1, MPI_INT, buffer.data(), size, &position, comm);
    for (const segment &seg : unit.pt.content)
    {
        int fields[2] = {seg.type, seg.length};
        MPI_Pack(fields, 2, MPI_INT, buffer.data(), size, &position, comm);
    }
    MPI_Pack(const_cast<int *>(&unit.pt.pivot), 1, MPI_INT, buffer.data(), size, &position, comm);

    int curr_count = static_cast<int>(unit.pt.curr_indices.size());
    MPI_Pack(&curr_count, 1, MPI_INT, buffer.data(), size, &position, comm);
    if (curr_count > 0)
    {
        MPI_Pack(const_cast<int *>(unit.pt.curr_indices.data()), curr_count, MPI_INT,
                 buffer.data(), size, &position, comm);
    }

    int max_count = static_cast<int>(unit.pt.max_indices.size());
    MPI_Pack(&max_count, 1, MPI_INT, buffer.data(), size, &position, comm);
    if (max_count > 0)
    {
        MPI_Pack(const_cast<int *>(unit.pt.max_indices.data()), max_count, MPI_INT,
                 buffer.data(), size, &position, comm);
    }

    float probabilities[2] = {unit.pt.preterm_prob, unit.pt.prob};
    MPI_Pack(probabilities, 2, MPI_FLOAT, buffer.data(), size, &position, comm);
    unsigned long long range[2] = {
        static_cast<unsigned long long>(unit.begin),
        static_cast<unsigned long long>(unit.end)};
    MPI_Pack(range, 2, MPI_UNSIGNED_LONG_LONG, buffer.data(), size, &position, comm);
    buffer.resize(position);
    return buffer;
}

WorkUnit UnpackWorkUnit(const std::vector<char> &buffer, MPI_Comm comm)
{
    WorkUnit unit;
    int position = 0;
    const int size = static_cast<int>(buffer.size());
    int content_count = 0;
    MPI_Unpack(const_cast<char *>(buffer.data()), size, &position, &content_count, 1, MPI_INT, comm);
    for (int i = 0; i < content_count; i += 1)
    {
        int fields[2] = {};
        MPI_Unpack(const_cast<char *>(buffer.data()), size, &position, fields, 2, MPI_INT, comm);
        unit.pt.insert(segment(fields[0], fields[1]));
    }
    MPI_Unpack(const_cast<char *>(buffer.data()), size, &position, &unit.pt.pivot, 1, MPI_INT, comm);

    int curr_count = 0;
    MPI_Unpack(const_cast<char *>(buffer.data()), size, &position, &curr_count, 1, MPI_INT, comm);
    unit.pt.curr_indices.resize(curr_count);
    if (curr_count > 0)
    {
        MPI_Unpack(const_cast<char *>(buffer.data()), size, &position, unit.pt.curr_indices.data(),
                   curr_count, MPI_INT, comm);
    }

    int max_count = 0;
    MPI_Unpack(const_cast<char *>(buffer.data()), size, &position, &max_count, 1, MPI_INT, comm);
    unit.pt.max_indices.resize(max_count);
    if (max_count > 0)
    {
        MPI_Unpack(const_cast<char *>(buffer.data()), size, &position, unit.pt.max_indices.data(),
                   max_count, MPI_INT, comm);
    }

    float probabilities[2] = {};
    MPI_Unpack(const_cast<char *>(buffer.data()), size, &position, probabilities, 2, MPI_FLOAT, comm);
    unit.pt.preterm_prob = probabilities[0];
    unit.pt.prob = probabilities[1];
    unsigned long long range[2] = {};
    MPI_Unpack(const_cast<char *>(buffer.data()), size, &position, range, 2,
               MPI_UNSIGNED_LONG_LONG, comm);
    unit.begin = static_cast<uint64_t>(range[0]);
    unit.end = static_cast<uint64_t>(range[1]);
    return unit;
}

std::vector<char> PackGuessBatch(const std::vector<std::string> &guesses, MPI_Comm comm)
{
    int size = 0;
    AddPackSize(1 + static_cast<int>(guesses.size()), MPI_INT, comm, size);
    for (const string &guess : guesses)
    {
        AddPackSize(static_cast<int>(guess.size()), MPI_CHAR, comm, size);
    }

    vector<char> buffer(size);
    int position = 0;
    int count = static_cast<int>(guesses.size());
    MPI_Pack(&count, 1, MPI_INT, buffer.data(), size, &position, comm);
    for (const string &guess : guesses)
    {
        int length = static_cast<int>(guess.size());
        MPI_Pack(&length, 1, MPI_INT, buffer.data(), size, &position, comm);
        if (length > 0)
        {
            MPI_Pack(const_cast<char *>(guess.data()), length, MPI_CHAR,
                     buffer.data(), size, &position, comm);
        }
    }
    buffer.resize(position);
    return buffer;
}

std::vector<std::string> UnpackGuessBatch(const std::vector<char> &buffer, MPI_Comm comm)
{
    vector<string> guesses;
    int position = 0;
    const int size = static_cast<int>(buffer.size());
    int count = 0;
    MPI_Unpack(const_cast<char *>(buffer.data()), size, &position, &count, 1, MPI_INT, comm);
    guesses.reserve(count);
    for (int i = 0; i < count; i += 1)
    {
        int length = 0;
        MPI_Unpack(const_cast<char *>(buffer.data()), size, &position, &length, 1, MPI_INT, comm);
        string guess(static_cast<size_t>(length), '\0');
        if (length > 0)
        {
            MPI_Unpack(const_cast<char *>(buffer.data()), size, &position, &guess[0],
                       length, MPI_CHAR, comm);
        }
        guesses.emplace_back(guess);
    }
    return guesses;
}

double HashGuesses(const std::vector<std::string> &guesses, bool use_simd)
{
    const auto start = steady_clock::now();
    if (use_simd)
    {
        uint32x4_t state[4];
        size_t i = 0;
        for (; i + 3 < guesses.size(); i += 4)
        {
            MD5Hash_simdversion(&guesses[i], state);
        }
        bit32 tail_state[4];
        for (; i < guesses.size(); i += 1)
        {
            MD5Hash(guesses[i], tail_state);
        }
    }
    else
    {
        bit32 state[4];
        for (const string &guess : guesses)
        {
            MD5Hash(guess, state);
        }
    }
    return duration<double>(steady_clock::now() - start).count();
}

WorkerStats ProcessWorkUnit(PriorityQueue &queue, const WorkUnit &unit, bool use_simd,
                            uint64_t chunk_size)
{
    WorkerStats stats;
    for (uint64_t begin = unit.begin; begin < unit.end; begin += chunk_size)
    {
        WorkUnit chunk = unit;
        chunk.begin = begin;
        chunk.end = min(begin + chunk_size, unit.end);
        vector<string> guesses;
        const auto generate_start = steady_clock::now();
        queue.GenerateRange(chunk, guesses);
        stats.generate_seconds += duration<double>(steady_clock::now() - generate_start).count();
        stats.hash_seconds += HashGuesses(guesses, use_simd);
        stats.count += guesses.size();
    }
    return stats;
}

void SendWorkUnitBlocking(int destination, const WorkUnit &unit, MPI_Comm comm)
{
    vector<char> buffer = PackWorkUnit(unit, comm);
    MPI_Send(buffer.data(), static_cast<int>(buffer.size()), MPI_PACKED,
             destination, TAG_WORK, comm);
}

bool ReceiveWorkUnitBlocking(int source, WorkUnit &unit, MPI_Comm comm)
{
    MPI_Status status;
    MPI_Probe(source, MPI_ANY_TAG, comm, &status);
    if (status.MPI_TAG == TAG_STOP)
    {
        MPI_Recv(nullptr, 0, MPI_BYTE, source, TAG_STOP, comm, MPI_STATUS_IGNORE);
        return false;
    }
    int count = 0;
    MPI_Get_count(&status, MPI_PACKED, &count);
    vector<char> buffer(count);
    MPI_Recv(buffer.data(), count, MPI_PACKED, source, TAG_WORK, comm, MPI_STATUS_IGNORE);
    unit = UnpackWorkUnit(buffer, comm);
    return true;
}

void SendStopBlocking(int destination, MPI_Comm comm)
{
    MPI_Send(nullptr, 0, MPI_BYTE, destination, TAG_STOP, comm);
}

void SendStatsBlocking(int destination, const WorkerStats &stats, MPI_Comm comm)
{
    MPI_Send(const_cast<WorkerStats *>(&stats), static_cast<int>(sizeof(stats)), MPI_BYTE,
             destination, TAG_RESULT, comm);
}

WorkerStats ReceiveStatsBlocking(int source, MPI_Status *status, MPI_Comm comm)
{
    WorkerStats stats;
    MPI_Recv(&stats, static_cast<int>(sizeof(stats)), MPI_BYTE, source, TAG_RESULT, comm, status);
    return stats;
}

}
