#ifndef PCFG_GPU_GENERATE_H
#define PCFG_GPU_GENERATE_H

#include <cstddef>
#include <string>
#include <vector>

constexpr int PCFG_GPU_MAX_GUESS_LEN = 64;
constexpr int PCFG_GPU_MAX_VALUE_LEN = 32;

struct GpuTimingResult
{
    double host_pack_ms = 0.0;
    double host_unpack_ms = 0.0;
    float h2d_ms = 0.0f;
    float kernel_ms = 0.0f;
    float d2h_ms = 0.0f;
    float total_gpu_ms = 0.0f;
    double cpu_overlap_ms = 0.0;
    int gpu_pt_count = 0;
    int gpu_guess_count = 0;
    int cpu_pt_count = 0;
    int cpu_guess_count = 0;
};

struct PcfgGpuPtBatch
{
    std::string prefix;
    std::vector<std::string> values;
};

struct PcfgSchedulingConfig
{
    std::size_t min_gpu_values = 4096;
    std::size_t target_gpu_values = 65536;
    std::size_t max_gpu_values = 131072;
};

struct PcfgScheduledWork
{
    std::vector<PcfgGpuPtBatch> cpu_pts;
    std::vector<std::vector<PcfgGpuPtBatch>> gpu_chunks;
};

std::size_t pcfg_count_values(const PcfgGpuPtBatch &pt);
std::size_t pcfg_count_values(const std::vector<PcfgGpuPtBatch> &pts);

std::vector<std::string> cpu_generate_guesses(const std::string &prefix,
                                              const std::vector<std::string> &values);

std::vector<std::string> cpu_generate_guesses_multi_pt(
    const std::vector<PcfgGpuPtBatch> &pts,
    std::vector<int> *output_pt_ids = nullptr);

PcfgScheduledWork schedule_pt_batches_for_gpu(const std::vector<PcfgGpuPtBatch> &pts,
                                              const PcfgSchedulingConfig &config);

bool gpu_generate_guesses(const std::string &prefix,
                          const std::vector<std::string> &values,
                          std::vector<std::string> &outputs,
                          GpuTimingResult *timing = nullptr,
                          std::string *error_message = nullptr);

bool gpu_generate_guesses_multi_pt(const std::vector<PcfgGpuPtBatch> &pts,
                                   std::vector<std::string> &outputs,
                                   std::vector<int> *output_pt_ids = nullptr,
                                   GpuTimingResult *timing = nullptr,
                                   std::string *error_message = nullptr);

bool gpu_generate_guesses_multi_pt_overlapped(
    const std::vector<std::vector<PcfgGpuPtBatch>> &gpu_chunks,
    std::vector<std::string> &outputs,
    std::vector<int> *output_pt_ids = nullptr,
    GpuTimingResult *timing = nullptr,
    std::string *error_message = nullptr);

bool compare_guess_batches(const std::vector<std::string> &expected,
                           const std::vector<std::string> &actual,
                           std::size_t *matched = nullptr);

#endif
