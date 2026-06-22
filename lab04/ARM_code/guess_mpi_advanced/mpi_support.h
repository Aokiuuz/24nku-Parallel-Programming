#ifndef MPI_SUPPORT_H
#define MPI_SUPPORT_H

#include "PCFG.h"
#include <mpi.h>
#include <cstdint>
#include <string>
#include <vector>

namespace mpi_guess
{

enum MessageTag
{
    TAG_WORK = 100,
    TAG_RESULT = 101,
    TAG_STOP = 102,
    TAG_BATCH = 103
};

struct RuntimeOptions
{
    uint64_t generate_limit = 10000000;
    uint64_t batch_guesses = 100000;
    int batch_units = 64;
    int gen_threads = 3;
    bool use_simd = true;
};

struct WorkerStats
{
    uint64_t count = 0;
    double generate_seconds = 0;
    double hash_seconds = 0;
};

RuntimeOptions ParseOptions(int argc, char **argv);

std::vector<char> PackWorkUnit(const WorkUnit &unit, MPI_Comm comm);
WorkUnit UnpackWorkUnit(const std::vector<char> &buffer, MPI_Comm comm);

std::vector<char> PackGuessBatch(const std::vector<std::string> &guesses, MPI_Comm comm);
std::vector<std::string> UnpackGuessBatch(const std::vector<char> &buffer, MPI_Comm comm);

double HashGuesses(const std::vector<std::string> &guesses, bool use_simd);
WorkerStats ProcessWorkUnit(PriorityQueue &queue, const WorkUnit &unit, bool use_simd,
                            uint64_t chunk_size = 65536);

void SendWorkUnitBlocking(int destination, const WorkUnit &unit, MPI_Comm comm);
bool ReceiveWorkUnitBlocking(int source, WorkUnit &unit, MPI_Comm comm);
void SendStopBlocking(int destination, MPI_Comm comm);
void SendStatsBlocking(int destination, const WorkerStats &stats, MPI_Comm comm);
WorkerStats ReceiveStatsBlocking(int source, MPI_Status *status, MPI_Comm comm);

}

#endif
