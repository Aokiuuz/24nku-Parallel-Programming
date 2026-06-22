#include "PCFG.h"
#include "mpi_support.h"
#include <mpi.h>
#include <pthread.h>
#include <unistd.h>
#include <algorithm>
#include <chrono>
#include <deque>
#include <iostream>
#include <memory>
#include <vector>

using namespace std;
using namespace chrono;
using namespace mpi_guess;

#include "correctness.cpp"

struct GeneratedBatch
{
    vector<string> guesses;
};

struct GeneratorContext
{
    PriorityQueue *queue = nullptr;
    deque<WorkUnit> tasks;
    deque<GeneratedBatch> ready;
    pthread_mutex_t mutex;
    pthread_cond_t ready_space;
    size_t max_ready = 2;
    uint64_t batch_guesses = 100000;
    int batch_units = 64;
    bool done = false;
    double generate_seconds = 0;
};

static void PushReadyBatch(GeneratorContext &context, vector<string> &guesses)
{
    if (guesses.empty())
    {
        return;
    }
    pthread_mutex_lock(&context.mutex);
    while (context.ready.size() >= context.max_ready)
    {
        pthread_cond_wait(&context.ready_space, &context.mutex);
    }
    GeneratedBatch batch;
    batch.guesses.swap(guesses);
    context.ready.emplace_back(std::move(batch));
    pthread_mutex_unlock(&context.mutex);
}

static void *GeneratorMain(void *argument)
{
    GeneratorContext &context = *static_cast<GeneratorContext *>(argument);
    vector<string> batch;
    int units_in_batch = 0;

    while (true)
    {
        pthread_mutex_lock(&context.mutex);
        if (context.tasks.empty())
        {
            pthread_mutex_unlock(&context.mutex);
            break;
        }
        WorkUnit unit = context.tasks.front();
        context.tasks.pop_front();
        pthread_mutex_unlock(&context.mutex);

        const auto generate_start = steady_clock::now();
        context.queue->GenerateRange(unit, batch);
        context.generate_seconds += duration<double>(steady_clock::now() - generate_start).count();
        units_in_batch += 1;

        if (batch.size() >= context.batch_guesses || units_in_batch >= context.batch_units)
        {
            PushReadyBatch(context, batch);
            units_in_batch = 0;
        }
    }

    PushReadyBatch(context, batch);
    pthread_mutex_lock(&context.mutex);
    context.done = true;
    pthread_mutex_unlock(&context.mutex);
    return nullptr;
}

static bool PopReadyBatch(vector<unique_ptr<GeneratorContext>> &contexts, size_t &cursor,
                          GeneratedBatch &batch)
{
    for (size_t offset = 0; offset < contexts.size(); offset += 1)
    {
        const size_t index = (cursor + offset) % contexts.size();
        GeneratorContext &context = *contexts[index];
        pthread_mutex_lock(&context.mutex);
        if (!context.ready.empty())
        {
            batch = std::move(context.ready.front());
            context.ready.pop_front();
            pthread_cond_signal(&context.ready_space);
            pthread_mutex_unlock(&context.mutex);
            cursor = (index + 1) % contexts.size();
            return true;
        }
        pthread_mutex_unlock(&context.mutex);
    }
    return false;
}

static bool GeneratorsDrained(vector<unique_ptr<GeneratorContext>> &contexts)
{
    for (const unique_ptr<GeneratorContext> &ptr : contexts)
    {
        GeneratorContext &context = *ptr;
        pthread_mutex_lock(&context.mutex);
        const bool drained = context.done && context.ready.empty();
        pthread_mutex_unlock(&context.mutex);
        if (!drained)
        {
            return false;
        }
    }
    return true;
}

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

static WorkerStats RunSingleProcess(PriorityQueue &queue, const RuntimeOptions &options)
{
    WorkerStats total;
    uint64_t scheduled = 0;
    while (scheduled < options.generate_limit && !queue.priority.empty())
    {
        const PT pt = queue.PopNextTask();
        const uint64_t count = queue.GuessCount(pt);
        scheduled += count;
        const vector<WorkUnit> units = queue.SplitTask(pt, options.batch_guesses);
        for (const WorkUnit &unit : units)
        {
            const WorkerStats stats = ProcessWorkUnit(queue, unit, options.use_simd);
            total.count += stats.count;
            total.generate_seconds += stats.generate_seconds;
            total.hash_seconds += stats.hash_seconds;
        }
    }
    return total;
}

static void RunEncryptionWorker(const RuntimeOptions &options)
{
    while (true)
    {
        MPI_Status status;
        MPI_Probe(0, MPI_ANY_TAG, MPI_COMM_WORLD, &status);
        if (status.MPI_TAG == TAG_STOP)
        {
            MPI_Recv(nullptr, 0, MPI_BYTE, 0, TAG_STOP, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
            break;
        }

        int count = 0;
        MPI_Get_count(&status, MPI_PACKED, &count);
        vector<char> packed(count);
        MPI_Recv(packed.data(), count, MPI_PACKED, 0, TAG_BATCH,
                 MPI_COMM_WORLD, MPI_STATUS_IGNORE);
        const vector<string> guesses = UnpackGuessBatch(packed, MPI_COMM_WORLD);

        WorkerStats stats;
        stats.count = guesses.size();
        stats.hash_seconds = HashGuesses(guesses, options.use_simd);
        SendStatsBlocking(0, stats, MPI_COMM_WORLD);
    }
}

static void AssignWorkUnits(PriorityQueue &queue, const RuntimeOptions &options,
                            vector<unique_ptr<GeneratorContext>> &contexts)
{
    vector<uint64_t> assigned(contexts.size(), 0);
    uint64_t scheduled = 0;
    while (scheduled < options.generate_limit && !queue.priority.empty())
    {
        const PT pt = queue.PopNextTask();
        const uint64_t count = queue.GuessCount(pt);
        scheduled += count;
        const vector<WorkUnit> units = queue.SplitTask(pt, options.batch_guesses);
        for (const WorkUnit &unit : units)
        {
            const size_t index = static_cast<size_t>(
                min_element(assigned.begin(), assigned.end()) - assigned.begin());
            contexts[index]->tasks.emplace_back(unit);
            assigned[index] += queue.GuessCount(unit);
        }
    }
}

static void CompleteWorker(int worker, vector<MPI_Request> &send_requests,
                           vector<MPI_Request> &result_requests,
                           vector<WorkerStats> &result_slots,
                           vector<WorkerStats> &worker_totals,
                           vector<bool> &idle, int &active_workers, uint64_t &completed)
{
    MPI_Wait(&send_requests[worker], MPI_STATUS_IGNORE);
    const WorkerStats &stats = result_slots[worker];
    worker_totals[worker].count += stats.count;
    worker_totals[worker].hash_seconds += stats.hash_seconds;
    completed += stats.count;
    idle[worker] = true;
    active_workers -= 1;
    result_requests[worker] = MPI_REQUEST_NULL;
}

static WorkerStats RunPipelineMaster(PriorityQueue &queue, const RuntimeOptions &options,
                                     int world_size, double &communication_seconds)
{
    vector<unique_ptr<GeneratorContext>> contexts;
    vector<pthread_t> generator_threads(static_cast<size_t>(options.gen_threads));
    for (int i = 0; i < options.gen_threads; i += 1)
    {
        unique_ptr<GeneratorContext> context(new GeneratorContext);
        context->queue = &queue;
        context->batch_guesses = options.batch_guesses;
        context->batch_units = options.batch_units;
        pthread_mutex_init(&context->mutex, nullptr);
        pthread_cond_init(&context->ready_space, nullptr);
        contexts.emplace_back(std::move(context));
    }
    AssignWorkUnits(queue, options, contexts);

    for (int i = 0; i < options.gen_threads; i += 1)
    {
        pthread_create(&generator_threads[static_cast<size_t>(i)], nullptr,
                       GeneratorMain, contexts[static_cast<size_t>(i)].get());
    }

    vector<vector<char>> outbound(static_cast<size_t>(world_size));
    vector<MPI_Request> send_requests(static_cast<size_t>(world_size), MPI_REQUEST_NULL);
    vector<MPI_Request> result_requests(static_cast<size_t>(world_size), MPI_REQUEST_NULL);
    vector<WorkerStats> result_slots(static_cast<size_t>(world_size));
    vector<WorkerStats> worker_totals(static_cast<size_t>(world_size));
    vector<bool> idle(static_cast<size_t>(world_size), true);
    idle[0] = false;

    int active_workers = 0;
    uint64_t completed = 0;
    uint64_t next_report = 100000;
    size_t ready_cursor = 0;

    while (true)
    {
        bool progress = false;
        for (int worker = 1; worker < world_size; worker += 1)
        {
            if (!idle[worker])
            {
                continue;
            }
            GeneratedBatch batch;
            if (!PopReadyBatch(contexts, ready_cursor, batch))
            {
                break;
            }

            const auto communication_start = steady_clock::now();
            outbound[worker] = PackGuessBatch(batch.guesses, MPI_COMM_WORLD);
            result_slots[worker] = WorkerStats();
            MPI_Irecv(&result_slots[worker], static_cast<int>(sizeof(WorkerStats)), MPI_BYTE,
                      worker, TAG_RESULT, MPI_COMM_WORLD, &result_requests[worker]);
            MPI_Isend(outbound[worker].data(), static_cast<int>(outbound[worker].size()),
                      MPI_PACKED, worker, TAG_BATCH, MPI_COMM_WORLD, &send_requests[worker]);
            communication_seconds +=
                duration<double>(steady_clock::now() - communication_start).count();
            idle[worker] = false;
            active_workers += 1;
            progress = true;
        }

        int completed_worker = MPI_UNDEFINED;
        int completed_flag = 0;
        MPI_Testany(world_size, result_requests.data(), &completed_worker,
                    &completed_flag, MPI_STATUS_IGNORE);
        if (completed_flag && completed_worker != MPI_UNDEFINED)
        {
            const auto communication_start = steady_clock::now();
            CompleteWorker(completed_worker, send_requests, result_requests, result_slots,
                           worker_totals, idle, active_workers, completed);
            communication_seconds +=
                duration<double>(steady_clock::now() - communication_start).count();
            progress = true;
        }

        if (completed >= next_report)
        {
            cout << "Guesses generated: " << completed << endl;
            next_report = completed + 100000;
        }

        const bool drained = GeneratorsDrained(contexts);
        if (drained && active_workers == 0)
        {
            break;
        }

        if (!progress)
        {
            const bool all_workers_busy = active_workers == world_size - 1;
            if (active_workers > 0 && (all_workers_busy || drained))
            {
                const auto communication_start = steady_clock::now();
                MPI_Waitany(world_size, result_requests.data(), &completed_worker,
                            MPI_STATUS_IGNORE);
                if (completed_worker != MPI_UNDEFINED)
                {
                    CompleteWorker(completed_worker, send_requests, result_requests, result_slots,
                                   worker_totals, idle, active_workers, completed);
                }
                communication_seconds +=
                    duration<double>(steady_clock::now() - communication_start).count();
            }
            else
            {
                usleep(1000);
            }
        }
    }

    vector<MPI_Request> stop_requests(static_cast<size_t>(world_size - 1), MPI_REQUEST_NULL);
    for (int worker = 1; worker < world_size; worker += 1)
    {
        MPI_Isend(nullptr, 0, MPI_BYTE, worker, TAG_STOP, MPI_COMM_WORLD,
                  &stop_requests[static_cast<size_t>(worker - 1)]);
    }
    MPI_Waitall(world_size - 1, stop_requests.data(), MPI_STATUSES_IGNORE);

    WorkerStats critical_path;
    critical_path.count = completed;
    for (int i = 0; i < options.gen_threads; i += 1)
    {
        pthread_join(generator_threads[static_cast<size_t>(i)], nullptr);
        critical_path.generate_seconds =
            max(critical_path.generate_seconds, contexts[static_cast<size_t>(i)]->generate_seconds);
        pthread_cond_destroy(&contexts[static_cast<size_t>(i)]->ready_space);
        pthread_mutex_destroy(&contexts[static_cast<size_t>(i)]->mutex);
    }
    for (int worker = 1; worker < world_size; worker += 1)
    {
        critical_path.hash_seconds =
            max(critical_path.hash_seconds, worker_totals[worker].hash_seconds);
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
        result = RunPipelineMaster(queue, options, world_size, communication_seconds);
    }
    else
    {
        RunEncryptionWorker(options);
    }
    const double wall_seconds = duration<double>(steady_clock::now() - wall_start).count();

    if (rank == 0)
    {
        cout << "Guess time:" << result.generate_seconds << "seconds" << endl;
        cout << "Hash time:" << result.hash_seconds << "seconds" << endl;
        cout << "Train time:" << train_seconds << "seconds" << endl;
        cout << "MPI communication time:" << communication_seconds << "seconds" << endl;
        cout << "MPI wall time:" << wall_seconds << "seconds" << endl;
        cout << "MPI processes:" << world_size << endl;
        cout << "Generator threads:" << options.gen_threads << endl;
        cout << "Processed guesses:" << result.count << endl;
    }

    MPI_Finalize();
    return 0;
}
