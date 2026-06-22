#include "pcfg_gpu_generate.h"

#include <hip/hip_runtime.h>

#include <algorithm>
#include <chrono>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <numeric>
#include <sstream>
#include <utility>

#define HIP_CHECK(cmd) do { \
    hipError_t e = cmd; \
    if (e != hipSuccess) { \
        std::cerr << "HIP error: " << hipGetErrorString(e) \
                  << " at " << __FILE__ << ":" << __LINE__ << std::endl; \
        std::exit(1); \
    } \
} while (0)

namespace
{

struct PackedHostBatch
{
    int pt_count = 0;
    int item_count = 0;
    std::vector<char> prefixes;
    std::vector<int> prefix_lens;
    std::vector<char> values;
    std::vector<int> value_lens;
    std::vector<int> item_pt_ids;
    std::vector<char> output;
    std::vector<int> output_lens;
};

struct DeviceBatch
{
    char *prefixes = nullptr;
    int *prefix_lens = nullptr;
    char *values = nullptr;
    int *value_lens = nullptr;
    int *item_pt_ids = nullptr;
    char *output = nullptr;
    int *output_lens = nullptr;
};

static void add_timing(GpuTimingResult *dst, const GpuTimingResult &src)
{
    if (dst == nullptr)
    {
        return;
    }
    dst->host_pack_ms += src.host_pack_ms;
    dst->host_unpack_ms += src.host_unpack_ms;
    dst->h2d_ms += src.h2d_ms;
    dst->kernel_ms += src.kernel_ms;
    dst->d2h_ms += src.d2h_ms;
    dst->total_gpu_ms += src.total_gpu_ms;
    dst->cpu_overlap_ms += src.cpu_overlap_ms;
    dst->gpu_pt_count += src.gpu_pt_count;
    dst->gpu_guess_count += src.gpu_guess_count;
    dst->cpu_pt_count += src.cpu_pt_count;
    dst->cpu_guess_count += src.cpu_guess_count;
}

static bool set_error(std::string *error_message, const std::string &message)
{
    if (error_message != nullptr)
    {
        *error_message = message;
    }
    return false;
}

static bool validate_pt_batches(const std::vector<PcfgGpuPtBatch> &pts,
                                std::string *error_message)
{
    for (std::size_t p = 0; p < pts.size(); p += 1)
    {
        const PcfgGpuPtBatch &pt = pts[p];
        if (pt.prefix.size() > static_cast<std::size_t>(PCFG_GPU_MAX_GUESS_LEN))
        {
            std::ostringstream os;
            os << "PT " << p << " prefix length exceeds PCFG_GPU_MAX_GUESS_LEN";
            return set_error(error_message, os.str());
        }
        for (std::size_t i = 0; i < pt.values.size(); i += 1)
        {
            if (pt.values[i].size() > static_cast<std::size_t>(PCFG_GPU_MAX_VALUE_LEN))
            {
                std::ostringstream os;
                os << "PT " << p << " value " << i
                   << " exceeds PCFG_GPU_MAX_VALUE_LEN";
                return set_error(error_message, os.str());
            }
            if (pt.prefix.size() + pt.values[i].size() >
                static_cast<std::size_t>(PCFG_GPU_MAX_GUESS_LEN))
            {
                std::ostringstream os;
                os << "PT " << p << " prefix + value " << i
                   << " exceeds PCFG_GPU_MAX_GUESS_LEN";
                return set_error(error_message, os.str());
            }
        }
    }
    return true;
}

static bool pack_host_batch(const std::vector<PcfgGpuPtBatch> &pts,
                            PackedHostBatch &packed,
                            std::string *error_message)
{
    packed = PackedHostBatch();
    if (!validate_pt_batches(pts, error_message))
    {
        return false;
    }

    packed.pt_count = static_cast<int>(pts.size());
    packed.item_count = static_cast<int>(pcfg_count_values(pts));
    packed.prefixes.assign(static_cast<std::size_t>(packed.pt_count) *
                               PCFG_GPU_MAX_GUESS_LEN,
                           0);
    packed.prefix_lens.assign(static_cast<std::size_t>(packed.pt_count), 0);
    packed.values.assign(static_cast<std::size_t>(packed.item_count) *
                             PCFG_GPU_MAX_VALUE_LEN,
                         0);
    packed.value_lens.assign(static_cast<std::size_t>(packed.item_count), 0);
    packed.item_pt_ids.assign(static_cast<std::size_t>(packed.item_count), 0);
    packed.output.assign(static_cast<std::size_t>(packed.item_count) *
                             PCFG_GPU_MAX_GUESS_LEN,
                         0);
    packed.output_lens.assign(static_cast<std::size_t>(packed.item_count), 0);

    int item_index = 0;
    for (int p = 0; p < packed.pt_count; p += 1)
    {
        const PcfgGpuPtBatch &pt = pts[static_cast<std::size_t>(p)];
        packed.prefix_lens[static_cast<std::size_t>(p)] =
            static_cast<int>(pt.prefix.size());
        if (!pt.prefix.empty())
        {
            std::memcpy(packed.prefixes.data() +
                            static_cast<std::size_t>(p) * PCFG_GPU_MAX_GUESS_LEN,
                        pt.prefix.data(), pt.prefix.size());
        }

        for (const std::string &value : pt.values)
        {
            packed.item_pt_ids[static_cast<std::size_t>(item_index)] = p;
            packed.value_lens[static_cast<std::size_t>(item_index)] =
                static_cast<int>(value.size());
            if (!value.empty())
            {
                std::memcpy(packed.values.data() +
                                static_cast<std::size_t>(item_index) *
                                    PCFG_GPU_MAX_VALUE_LEN,
                            value.data(), value.size());
            }
            item_index += 1;
        }
    }
    return true;
}

static void allocate_device_batch(const PackedHostBatch &packed, DeviceBatch &device)
{
    device = DeviceBatch();
    if (packed.item_count == 0)
    {
        return;
    }
    HIP_CHECK(hipMalloc(reinterpret_cast<void **>(&device.prefixes),
                        packed.prefixes.size()));
    HIP_CHECK(hipMalloc(reinterpret_cast<void **>(&device.prefix_lens),
                        packed.prefix_lens.size() * sizeof(int)));
    HIP_CHECK(hipMalloc(reinterpret_cast<void **>(&device.values),
                        packed.values.size()));
    HIP_CHECK(hipMalloc(reinterpret_cast<void **>(&device.value_lens),
                        packed.value_lens.size() * sizeof(int)));
    HIP_CHECK(hipMalloc(reinterpret_cast<void **>(&device.item_pt_ids),
                        packed.item_pt_ids.size() * sizeof(int)));
    HIP_CHECK(hipMalloc(reinterpret_cast<void **>(&device.output),
                        packed.output.size()));
    HIP_CHECK(hipMalloc(reinterpret_cast<void **>(&device.output_lens),
                        packed.output_lens.size() * sizeof(int)));
}

static void free_device_batch(DeviceBatch &device)
{
    if (device.prefixes != nullptr) HIP_CHECK(hipFree(device.prefixes));
    if (device.prefix_lens != nullptr) HIP_CHECK(hipFree(device.prefix_lens));
    if (device.values != nullptr) HIP_CHECK(hipFree(device.values));
    if (device.value_lens != nullptr) HIP_CHECK(hipFree(device.value_lens));
    if (device.item_pt_ids != nullptr) HIP_CHECK(hipFree(device.item_pt_ids));
    if (device.output != nullptr) HIP_CHECK(hipFree(device.output));
    if (device.output_lens != nullptr) HIP_CHECK(hipFree(device.output_lens));
    device = DeviceBatch();
}

static void unpack_outputs(const PackedHostBatch &packed,
                           std::vector<std::string> &outputs,
                           std::vector<int> *output_pt_ids)
{
    outputs.reserve(outputs.size() + static_cast<std::size_t>(packed.item_count));
    if (output_pt_ids != nullptr)
    {
        output_pt_ids->reserve(output_pt_ids->size() +
                               static_cast<std::size_t>(packed.item_count));
    }

    for (int i = 0; i < packed.item_count; i += 1)
    {
        const int len = packed.output_lens[static_cast<std::size_t>(i)];
        outputs.emplace_back(packed.output.data() +
                                 static_cast<std::size_t>(i) *
                                     PCFG_GPU_MAX_GUESS_LEN,
                             static_cast<std::size_t>(len));
        if (output_pt_ids != nullptr)
        {
            output_pt_ids->push_back(packed.item_pt_ids[static_cast<std::size_t>(i)]);
        }
    }
}

} // namespace

__global__ void generate_guesses_multi_pt_kernel(const char *prefixes,
                                                 const int *prefix_lens,
                                                 const char *values,
                                                 const int *value_lens,
                                                 const int *item_pt_ids,
                                                 int item_count,
                                                 char *output,
                                                 int *output_lens)
{
    const int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= item_count)
    {
        return;
    }

    const int pt_id = item_pt_ids[idx];
    const char *prefix = prefixes + pt_id * PCFG_GPU_MAX_GUESS_LEN;
    const int prefix_len = prefix_lens[pt_id];
    const char *value = values + idx * PCFG_GPU_MAX_VALUE_LEN;
    const int value_len = value_lens[idx];
    char *out = output + idx * PCFG_GPU_MAX_GUESS_LEN;

    for (int i = 0; i < prefix_len; i += 1)
    {
        out[i] = prefix[i];
    }
    for (int j = 0; j < value_len; j += 1)
    {
        out[prefix_len + j] = value[j];
    }

    const int len = prefix_len + value_len;
    output_lens[idx] = len;
    if (len < PCFG_GPU_MAX_GUESS_LEN)
    {
        out[len] = '\0';
    }
}

std::size_t pcfg_count_values(const PcfgGpuPtBatch &pt)
{
    return pt.values.size();
}

std::size_t pcfg_count_values(const std::vector<PcfgGpuPtBatch> &pts)
{
    std::size_t total = 0;
    for (const PcfgGpuPtBatch &pt : pts)
    {
        total += pt.values.size();
    }
    return total;
}

std::vector<std::string> cpu_generate_guesses(const std::string &prefix,
                                              const std::vector<std::string> &values)
{
    PcfgGpuPtBatch pt{prefix, values};
    return cpu_generate_guesses_multi_pt({pt}, nullptr);
}

std::vector<std::string> cpu_generate_guesses_multi_pt(
    const std::vector<PcfgGpuPtBatch> &pts,
    std::vector<int> *output_pt_ids)
{
    std::vector<std::string> outputs;
    outputs.reserve(pcfg_count_values(pts));
    if (output_pt_ids != nullptr)
    {
        output_pt_ids->clear();
        output_pt_ids->reserve(pcfg_count_values(pts));
    }

    for (std::size_t p = 0; p < pts.size(); p += 1)
    {
        for (const std::string &value : pts[p].values)
        {
            outputs.emplace_back(pts[p].prefix + value);
            if (output_pt_ids != nullptr)
            {
                output_pt_ids->push_back(static_cast<int>(p));
            }
        }
    }
    return outputs;
}

PcfgScheduledWork schedule_pt_batches_for_gpu(const std::vector<PcfgGpuPtBatch> &pts,
                                              const PcfgSchedulingConfig &config)
{
    PcfgScheduledWork scheduled;
    std::vector<PcfgGpuPtBatch> current_chunk;
    std::size_t current_values = 0;

    auto flush_chunk = [&]() {
        if (!current_chunk.empty())
        {
            scheduled.gpu_chunks.emplace_back(current_chunk);
            current_chunk.clear();
            current_values = 0;
        }
    };

    for (const PcfgGpuPtBatch &pt : pts)
    {
        const std::size_t count = pcfg_count_values(pt);
        if (count == 0)
        {
            continue;
        }
        if (count < config.min_gpu_values)
        {
            scheduled.cpu_pts.emplace_back(pt);
            continue;
        }

        if (count > config.max_gpu_values)
        {
            flush_chunk();
            for (std::size_t begin = 0; begin < count; begin += config.max_gpu_values)
            {
                const std::size_t end = std::min(begin + config.max_gpu_values, count);
                PcfgGpuPtBatch piece;
                piece.prefix = pt.prefix;
                piece.values.assign(pt.values.begin() + static_cast<std::ptrdiff_t>(begin),
                                    pt.values.begin() + static_cast<std::ptrdiff_t>(end));
                scheduled.gpu_chunks.push_back({piece});
            }
            continue;
        }

        if (!current_chunk.empty() &&
            current_values + count > config.target_gpu_values)
        {
            flush_chunk();
        }
        current_chunk.emplace_back(pt);
        current_values += count;
    }

    flush_chunk();
    return scheduled;
}

bool compare_guess_batches(const std::vector<std::string> &expected,
                           const std::vector<std::string> &actual,
                           std::size_t *matched)
{
    std::size_t local_matched = 0;
    const std::size_t limit = std::min(expected.size(), actual.size());
    for (std::size_t i = 0; i < limit; i += 1)
    {
        if (expected[i] == actual[i])
        {
            local_matched += 1;
        }
    }
    if (matched != nullptr)
    {
        *matched = local_matched;
    }
    return expected.size() == actual.size() && local_matched == expected.size();
}

bool gpu_generate_guesses(const std::string &prefix,
                          const std::vector<std::string> &values,
                          std::vector<std::string> &outputs,
                          GpuTimingResult *timing,
                          std::string *error_message)
{
    PcfgGpuPtBatch pt{prefix, values};
    return gpu_generate_guesses_multi_pt({pt}, outputs, nullptr, timing, error_message);
}

bool gpu_generate_guesses_multi_pt(const std::vector<PcfgGpuPtBatch> &pts,
                                   std::vector<std::string> &outputs,
                                   std::vector<int> *output_pt_ids,
                                   GpuTimingResult *timing,
                                   std::string *error_message)
{
    outputs.clear();
    if (output_pt_ids != nullptr)
    {
        output_pt_ids->clear();
    }
    if (timing != nullptr)
    {
        *timing = GpuTimingResult();
        timing->gpu_pt_count = static_cast<int>(pts.size());
        timing->gpu_guess_count = static_cast<int>(pcfg_count_values(pts));
    }

    PackedHostBatch packed;
    const auto pack_start = std::chrono::high_resolution_clock::now();
    if (!pack_host_batch(pts, packed, error_message))
    {
        return false;
    }
    const auto pack_stop = std::chrono::high_resolution_clock::now();
    if (timing != nullptr)
    {
        timing->host_pack_ms =
            std::chrono::duration<double, std::milli>(pack_stop - pack_start).count();
    }
    if (packed.item_count == 0)
    {
        return true;
    }

    DeviceBatch device;
    allocate_device_batch(packed, device);

    hipEvent_t start;
    hipEvent_t stop;
    HIP_CHECK(hipEventCreate(&start));
    HIP_CHECK(hipEventCreate(&stop));

    float h2d_ms = 0.0f;
    float kernel_ms = 0.0f;
    float d2h_ms = 0.0f;

    HIP_CHECK(hipEventRecord(start));
    HIP_CHECK(hipMemcpy(device.prefixes, packed.prefixes.data(), packed.prefixes.size(),
                        hipMemcpyHostToDevice));
    HIP_CHECK(hipMemcpy(device.prefix_lens, packed.prefix_lens.data(),
                        packed.prefix_lens.size() * sizeof(int), hipMemcpyHostToDevice));
    HIP_CHECK(hipMemcpy(device.values, packed.values.data(), packed.values.size(),
                        hipMemcpyHostToDevice));
    HIP_CHECK(hipMemcpy(device.value_lens, packed.value_lens.data(),
                        packed.value_lens.size() * sizeof(int), hipMemcpyHostToDevice));
    HIP_CHECK(hipMemcpy(device.item_pt_ids, packed.item_pt_ids.data(),
                        packed.item_pt_ids.size() * sizeof(int), hipMemcpyHostToDevice));
    HIP_CHECK(hipEventRecord(stop));
    HIP_CHECK(hipEventSynchronize(stop));
    HIP_CHECK(hipEventElapsedTime(&h2d_ms, start, stop));

    const int block_size = 256;
    const int grid_size = (packed.item_count + block_size - 1) / block_size;
    HIP_CHECK(hipEventRecord(start));
    generate_guesses_multi_pt_kernel<<<grid_size, block_size>>>(
        device.prefixes,
        device.prefix_lens,
        device.values,
        device.value_lens,
        device.item_pt_ids,
        packed.item_count,
        device.output,
        device.output_lens);
    HIP_CHECK(hipGetLastError());
    HIP_CHECK(hipEventRecord(stop));
    HIP_CHECK(hipEventSynchronize(stop));
    HIP_CHECK(hipDeviceSynchronize());
    HIP_CHECK(hipEventElapsedTime(&kernel_ms, start, stop));

    HIP_CHECK(hipEventRecord(start));
    HIP_CHECK(hipMemcpy(packed.output.data(), device.output, packed.output.size(),
                        hipMemcpyDeviceToHost));
    HIP_CHECK(hipMemcpy(packed.output_lens.data(), device.output_lens,
                        packed.output_lens.size() * sizeof(int), hipMemcpyDeviceToHost));
    HIP_CHECK(hipEventRecord(stop));
    HIP_CHECK(hipEventSynchronize(stop));
    HIP_CHECK(hipEventElapsedTime(&d2h_ms, start, stop));

    HIP_CHECK(hipEventDestroy(start));
    HIP_CHECK(hipEventDestroy(stop));
    free_device_batch(device);

    const auto unpack_start = std::chrono::high_resolution_clock::now();
    unpack_outputs(packed, outputs, output_pt_ids);
    const auto unpack_stop = std::chrono::high_resolution_clock::now();
    if (timing != nullptr)
    {
        timing->host_unpack_ms =
            std::chrono::duration<double, std::milli>(unpack_stop - unpack_start).count();
        timing->h2d_ms = h2d_ms;
        timing->kernel_ms = kernel_ms;
        timing->d2h_ms = d2h_ms;
        timing->total_gpu_ms = h2d_ms + kernel_ms + d2h_ms;
    }
    return true;
}

bool gpu_generate_guesses_multi_pt_overlapped(
    const std::vector<std::vector<PcfgGpuPtBatch>> &gpu_chunks,
    std::vector<std::string> &outputs,
    std::vector<int> *output_pt_ids,
    GpuTimingResult *timing,
    std::string *error_message)
{
    outputs.clear();
    if (output_pt_ids != nullptr)
    {
        output_pt_ids->clear();
    }
    if (timing != nullptr)
    {
        *timing = GpuTimingResult();
    }
    if (gpu_chunks.empty())
    {
        return true;
    }

    hipStream_t stream;
    HIP_CHECK(hipStreamCreateWithFlags(&stream, hipStreamNonBlocking));

    PackedHostBatch current;
    const auto initial_pack_start = std::chrono::high_resolution_clock::now();
    if (!pack_host_batch(gpu_chunks.front(), current, error_message))
    {
        HIP_CHECK(hipStreamDestroy(stream));
        return false;
    }
    const auto initial_pack_stop = std::chrono::high_resolution_clock::now();
    if (timing != nullptr)
    {
        timing->host_pack_ms +=
            std::chrono::duration<double, std::milli>(
                initial_pack_stop - initial_pack_start).count();
    }

    for (std::size_t chunk = 0; chunk < gpu_chunks.size(); chunk += 1)
    {
        DeviceBatch device;
        allocate_device_batch(current, device);

        hipEvent_t h2d_start, h2d_stop, kernel_start, kernel_stop, d2h_start, d2h_stop;
        HIP_CHECK(hipEventCreate(&h2d_start));
        HIP_CHECK(hipEventCreate(&h2d_stop));
        HIP_CHECK(hipEventCreate(&kernel_start));
        HIP_CHECK(hipEventCreate(&kernel_stop));
        HIP_CHECK(hipEventCreate(&d2h_start));
        HIP_CHECK(hipEventCreate(&d2h_stop));

        const int block_size = 256;
        const int grid_size = (current.item_count + block_size - 1) / block_size;

        HIP_CHECK(hipEventRecord(h2d_start, stream));
        HIP_CHECK(hipMemcpyAsync(device.prefixes, current.prefixes.data(),
                                 current.prefixes.size(), hipMemcpyHostToDevice, stream));
        HIP_CHECK(hipMemcpyAsync(device.prefix_lens, current.prefix_lens.data(),
                                 current.prefix_lens.size() * sizeof(int),
                                 hipMemcpyHostToDevice, stream));
        HIP_CHECK(hipMemcpyAsync(device.values, current.values.data(), current.values.size(),
                                 hipMemcpyHostToDevice, stream));
        HIP_CHECK(hipMemcpyAsync(device.value_lens, current.value_lens.data(),
                                 current.value_lens.size() * sizeof(int),
                                 hipMemcpyHostToDevice, stream));
        HIP_CHECK(hipMemcpyAsync(device.item_pt_ids, current.item_pt_ids.data(),
                                 current.item_pt_ids.size() * sizeof(int),
                                 hipMemcpyHostToDevice, stream));
        HIP_CHECK(hipEventRecord(h2d_stop, stream));

        HIP_CHECK(hipEventRecord(kernel_start, stream));
        generate_guesses_multi_pt_kernel<<<grid_size, block_size, 0, stream>>>(
            device.prefixes,
            device.prefix_lens,
            device.values,
            device.value_lens,
            device.item_pt_ids,
            current.item_count,
            device.output,
            device.output_lens);
        HIP_CHECK(hipGetLastError());
        HIP_CHECK(hipEventRecord(kernel_stop, stream));

        HIP_CHECK(hipEventRecord(d2h_start, stream));
        HIP_CHECK(hipMemcpyAsync(current.output.data(), device.output, current.output.size(),
                                 hipMemcpyDeviceToHost, stream));
        HIP_CHECK(hipMemcpyAsync(current.output_lens.data(), device.output_lens,
                                 current.output_lens.size() * sizeof(int),
                                 hipMemcpyDeviceToHost, stream));
        HIP_CHECK(hipEventRecord(d2h_stop, stream));

        PackedHostBatch next;
        const auto cpu_start = std::chrono::high_resolution_clock::now();
        if (chunk + 1 < gpu_chunks.size() &&
            !pack_host_batch(gpu_chunks[chunk + 1], next, error_message))
        {
            HIP_CHECK(hipStreamSynchronize(stream));
            free_device_batch(device);
            HIP_CHECK(hipStreamDestroy(stream));
            return false;
        }
        const auto cpu_stop = std::chrono::high_resolution_clock::now();

        HIP_CHECK(hipStreamSynchronize(stream));

        GpuTimingResult chunk_timing;
        HIP_CHECK(hipEventElapsedTime(&chunk_timing.h2d_ms, h2d_start, h2d_stop));
        HIP_CHECK(hipEventElapsedTime(&chunk_timing.kernel_ms, kernel_start, kernel_stop));
        HIP_CHECK(hipEventElapsedTime(&chunk_timing.d2h_ms, d2h_start, d2h_stop));
        chunk_timing.total_gpu_ms =
            chunk_timing.h2d_ms + chunk_timing.kernel_ms + chunk_timing.d2h_ms;
        chunk_timing.cpu_overlap_ms =
            std::chrono::duration<double, std::milli>(cpu_stop - cpu_start).count();
        chunk_timing.host_pack_ms = chunk_timing.cpu_overlap_ms;
        chunk_timing.gpu_pt_count = current.pt_count;
        chunk_timing.gpu_guess_count = current.item_count;

        const auto unpack_start = std::chrono::high_resolution_clock::now();
        unpack_outputs(current, outputs, output_pt_ids);
        const auto unpack_stop = std::chrono::high_resolution_clock::now();
        chunk_timing.host_unpack_ms =
            std::chrono::duration<double, std::milli>(
                unpack_stop - unpack_start).count();
        add_timing(timing, chunk_timing);

        HIP_CHECK(hipEventDestroy(h2d_start));
        HIP_CHECK(hipEventDestroy(h2d_stop));
        HIP_CHECK(hipEventDestroy(kernel_start));
        HIP_CHECK(hipEventDestroy(kernel_stop));
        HIP_CHECK(hipEventDestroy(d2h_start));
        HIP_CHECK(hipEventDestroy(d2h_stop));
        free_device_batch(device);
        current = std::move(next);
    }

    HIP_CHECK(hipStreamDestroy(stream));
    return true;
}
