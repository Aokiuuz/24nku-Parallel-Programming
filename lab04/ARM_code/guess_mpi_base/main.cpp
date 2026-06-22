#include "PCFG.h"
#include "mpi_support.h"
#include <mpi.h>
#include <algorithm>
#include <chrono>
#include <iostream>
#include <vector>

using namespace std;
using namespace chrono;
using namespace mpi_guess;

#include "correctness.cpp"

static void TrainModel(PriorityQueue &queue, int rank, double &train_seconds)
{
    if (rank != 0)
    {
        cout.setstate(ios_base::failbit);
    }
    const auto start = steady_clock::now();
    queue.m.train("/guessdata/Rockyou-singleLined-full.txt");
    queue.m.order();
    train_seconds = duration<double>(steady_clock::now() - start).count();
    if (rank != 0)
    {
        cout.clear();
    }
}

static bool NextWholePt(PriorityQueue &queue, uint64_t limit, uint64_t &scheduled, WorkUnit &unit)
{
    if (scheduled >= limit || queue.priority.empty())
    {
        return false;
    }
    unit.pt = queue.PopNextTask();
    unit.begin = 0;
    unit.end = queue.GuessCount(unit.pt);
    scheduled += queue.GuessCount(unit);
    return unit.end > unit.begin;
}

static WorkerStats RunSingleProcess(PriorityQueue &queue, const RuntimeOptions &options)
{
    WorkerStats total;
    uint64_t scheduled = 0;
    uint64_t next_report = 100000;
    WorkUnit unit;
    while (NextWholePt(queue, options.generate_limit, scheduled, unit))
    {
        const WorkerStats stats = ProcessWorkUnit(queue, unit, options.use_simd);
        total.count += stats.count;
        total.generate_seconds += stats.generate_seconds;
        total.hash_seconds += stats.hash_seconds;
        if (total.count >= next_report)
        {
            cout << "Guesses generated: " << total.count << endl;
            next_report = total.count + 100000;
        }
    }
    return total;
}

static void RunWorker(PriorityQueue &queue, const RuntimeOptions &options)
{
    WorkUnit unit;
    while (ReceiveWorkUnitBlocking(0, unit, MPI_COMM_WORLD))
    {
        const WorkerStats stats = ProcessWorkUnit(queue, unit, options.use_simd);
        SendStatsBlocking(0, stats, MPI_COMM_WORLD);
    }
}

static WorkerStats RunMaster(PriorityQueue &queue, const RuntimeOptions &options, int world_size,
                             double &communication_seconds)
{
    vector<WorkerStats> totals(static_cast<size_t>(world_size));
    uint64_t scheduled = 0;
    uint64_t completed = 0;
    uint64_t next_report = 100000;
    int active_workers = 0;

    for (int worker = 1; worker < world_size; worker += 1)
    {
        WorkUnit unit;
        if (NextWholePt(queue, options.generate_limit, scheduled, unit))
        {
            const auto communication_start = steady_clock::now();
            SendWorkUnitBlocking(worker, unit, MPI_COMM_WORLD);
            communication_seconds +=
                duration<double>(steady_clock::now() - communication_start).count();
            active_workers += 1;
        }
        else
        {
            const auto communication_start = steady_clock::now();
            SendStopBlocking(worker, MPI_COMM_WORLD);
            communication_seconds +=
                duration<double>(steady_clock::now() - communication_start).count();
        }
    }

    while (active_workers > 0)
    {
        MPI_Status status;
        const auto receive_start = steady_clock::now();
        const WorkerStats stats = ReceiveStatsBlocking(MPI_ANY_SOURCE, &status, MPI_COMM_WORLD);
        communication_seconds += duration<double>(steady_clock::now() - receive_start).count();
        const int worker = status.MPI_SOURCE;
        totals[worker].count += stats.count;
        totals[worker].generate_seconds += stats.generate_seconds;
        totals[worker].hash_seconds += stats.hash_seconds;
        completed += stats.count;

        if (completed >= next_report)
        {
            cout << "Guesses generated: " << completed << endl;
            next_report = completed + 100000;
        }

        WorkUnit unit;
        if (NextWholePt(queue, options.generate_limit, scheduled, unit))
        {
            const auto communication_start = steady_clock::now();
            SendWorkUnitBlocking(worker, unit, MPI_COMM_WORLD);
            communication_seconds +=
                duration<double>(steady_clock::now() - communication_start).count();
        }
        else
        {
            const auto communication_start = steady_clock::now();
            SendStopBlocking(worker, MPI_COMM_WORLD);
            communication_seconds +=
                duration<double>(steady_clock::now() - communication_start).count();
            active_workers -= 1;
        }
    }

    WorkerStats critical_path;
    critical_path.count = completed;
    for (int worker = 1; worker < world_size; worker += 1)
    {
        critical_path.generate_seconds =
            max(critical_path.generate_seconds, totals[worker].generate_seconds);
        critical_path.hash_seconds =
            max(critical_path.hash_seconds, totals[worker].hash_seconds);
    }
    return critical_path;
}

int main(int argc, char **argv)
{
    int provided = MPI_THREAD_SINGLE;
    MPI_Init_thread(&argc, &argv, MPI_THREAD_FUNNELED, &provided);

    int rank = 0;
    int world_size = 1;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &world_size);
    const RuntimeOptions options = ParseOptions(argc, argv);

    if (provided < MPI_THREAD_FUNNELED)
    {
        if (rank == 0)
        {
            cerr << "MPI implementation does not provide MPI_THREAD_FUNNELED." << endl;
        }
        MPI_Finalize();
        return 1;
    }

    int correctness_ok = 1;
    if (rank == 0)
    {
        correctness_ok = RunCorrectnessTests() ? 1 : 0;
    }
    MPI_Bcast(&correctness_ok, 1, MPI_INT, 0, MPI_COMM_WORLD);
    if (!correctness_ok)
    {
        MPI_Finalize();
        return 1;
    }

    PriorityQueue queue;
    double train_seconds = 0;
    TrainModel(queue, rank, train_seconds);
    if (rank == 0)
    {
        queue.init();
    }
    MPI_Barrier(MPI_COMM_WORLD);

    const auto wall_start = steady_clock::now();
    double communication_seconds = 0;
    WorkerStats result;
    if (world_size == 1)
    {
        result = RunSingleProcess(queue, options);
    }
    else if (rank == 0)
    {
        result = RunMaster(queue, options, world_size, communication_seconds);
    }
    else
    {
        RunWorker(queue, options);
    }
    const double wall_seconds = duration<double>(steady_clock::now() - wall_start).count();

    if (rank == 0)
    {
        cout << "Guess time:" << result.generate_seconds << "seconds" << endl;
        cout << "Hash time:" << result.hash_seconds << "seconds" << endl;
        cout << "Train time:" << train_seconds << "seconds" << endl;
        cout << "MPI communication/wait time:" << communication_seconds << "seconds" << endl;
        cout << "MPI wall time:" << wall_seconds << "seconds" << endl;
        cout << "MPI processes:" << world_size << endl;
        cout << "Processed guesses:" << result.count << endl;
    }

    MPI_Finalize();
    return 0;
}
