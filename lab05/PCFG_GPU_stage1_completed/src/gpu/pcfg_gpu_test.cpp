#include "pcfg_gpu_generate.h"

#include <algorithm>
#include <chrono>
#include <cstdlib>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

namespace
{

struct Options
{
    std::string mode = "check";
    int batch = 1024;
    int pts = 4;
    std::string prefix = "pcfg";
};

Options parse_options(int argc, char **argv)
{
    Options options;
    for (int i = 1; i < argc; i += 1)
    {
        const std::string arg = argv[i];
        if (arg == "--mode" && i + 1 < argc)
        {
            options.mode = argv[++i];
        }
        else if (arg == "--batch" && i + 1 < argc)
        {
            options.batch = std::stoi(argv[++i]);
        }
        else if (arg == "--pts" && i + 1 < argc)
        {
            options.pts = std::stoi(argv[++i]);
        }
        else if (arg == "--prefix" && i + 1 < argc)
        {
            options.prefix = argv[++i];
        }
        else if (arg == "--help")
        {
            std::cout
                << "Usage: pcfg_gpu_test --mode MODE [--batch N] [--pts N]\n"
                << "MODE: cpu, check, bench, multi-check, multi-bench,\n"
                << "      overlap-check, overlap-bench, schedule, schedule-bench\n";
            std::exit(0);
        }
    }
    return options;
}

std::vector<std::string> make_values(int batch, int seed = 0)
{
    std::vector<std::string> values;
    values.reserve(static_cast<std::size_t>(batch));
    for (int i = 0; i < batch; i += 1)
    {
        std::ostringstream os;
        os << "v" << seed << "_" << std::setw(8) << std::setfill('0') << i;
        values.emplace_back(os.str());
    }
    return values;
}

std::vector<PcfgGpuPtBatch> make_pt_batches(int pt_count, int batch_per_pt,
                                            const std::string &prefix)
{
    std::vector<PcfgGpuPtBatch> pts;
    pts.reserve(static_cast<std::size_t>(pt_count));
    for (int p = 0; p < pt_count; p += 1)
    {
        PcfgGpuPtBatch pt;
        pt.prefix = prefix + "_pt" + std::to_string(p) + "_";
        pt.values = make_values(batch_per_pt, p);
        pts.emplace_back(std::move(pt));
    }
    return pts;
}

std::vector<PcfgGpuPtBatch> make_skewed_pt_batches(const std::string &prefix)
{
    std::vector<PcfgGpuPtBatch> pts;
    const int sizes[] = {16, 128, 1024, 4096, 12000, 50000};
    for (int p = 0; p < 6; p += 1)
    {
        PcfgGpuPtBatch pt;
        pt.prefix = prefix + "_skew" + std::to_string(p) + "_";
        pt.values = make_values(sizes[p], p);
        pts.emplace_back(std::move(pt));
    }
    return pts;
}

uint64_t fnv1a_hash(const std::vector<std::string> &items)
{
    uint64_t hash = 1469598103934665603ULL;
    for (const std::string &item : items)
    {
        for (unsigned char ch : item)
        {
            hash ^= ch;
            hash *= 1099511628211ULL;
        }
        hash ^= 0xffU;
        hash *= 1099511628211ULL;
    }
    return hash;
}

double cpu_time_ms(const std::vector<PcfgGpuPtBatch> &pts,
                   std::vector<std::string> &outputs)
{
    const auto start = std::chrono::high_resolution_clock::now();
    outputs = cpu_generate_guesses_multi_pt(pts);
    const auto stop = std::chrono::high_resolution_clock::now();
    return std::chrono::duration<double, std::milli>(stop - start).count();
}

bool compare_sorted(std::vector<std::string> expected,
                    std::vector<std::string> actual,
                    std::size_t *matched)
{
    std::sort(expected.begin(), expected.end());
    std::sort(actual.begin(), actual.end());
    return compare_guess_batches(expected, actual, matched);
}

int run_cpu(const Options &options)
{
    const std::vector<PcfgGpuPtBatch> pts =
        make_pt_batches(1, options.batch, options.prefix);
    std::vector<std::string> cpu_outputs;
    const double cpu_ms = cpu_time_ms(pts, cpu_outputs);
    std::cout << std::fixed << std::setprecision(4);
    std::cout << "[cpu] batch=" << options.batch
              << " cpu_ms=" << cpu_ms
              << " hash=" << fnv1a_hash(cpu_outputs) << "\n";
    return 0;
}

int run_single(const Options &options, bool bench)
{
    const std::vector<std::string> values = make_values(options.batch);
    const std::vector<PcfgGpuPtBatch> pts = {{options.prefix, values}};
    std::vector<std::string> cpu_outputs;
    std::vector<std::string> gpu_outputs;
    const double cpu_ms = cpu_time_ms(pts, cpu_outputs);

    GpuTimingResult timing;
    std::string error;
    if (!gpu_generate_guesses(options.prefix, values, gpu_outputs, &timing, &error))
    {
        std::cerr << "[error] " << error << "\n";
        return 1;
    }

    std::size_t matched = 0;
    const bool ok = compare_guess_batches(cpu_outputs, gpu_outputs, &matched);
    std::cout << std::fixed << std::setprecision(4);
    if (!bench)
    {
        std::cout << "[check] batch=" << options.batch
                  << " matched=" << matched << "/" << cpu_outputs.size()
                  << " " << (ok ? "PASS" : "FAIL") << "\n";
        return ok ? 0 : 1;
    }

    const double speedup = timing.total_gpu_ms > 0.0f
                               ? cpu_ms / static_cast<double>(timing.total_gpu_ms)
                               : 0.0;
    std::cout << "[bench] batch=" << options.batch
              << " cpu_ms=" << cpu_ms
              << " h2d_ms=" << timing.h2d_ms
              << " kernel_ms=" << timing.kernel_ms
              << " d2h_ms=" << timing.d2h_ms
              << " gpu_total_ms=" << timing.total_gpu_ms
              << " speedup=" << speedup
              << " correctness=" << (ok ? "PASS" : "FAIL") << "\n";
    return ok ? 0 : 1;
}

int run_multi(const Options &options, bool overlap, bool bench)
{
    const std::vector<PcfgGpuPtBatch> pts =
        make_pt_batches(options.pts, options.batch, options.prefix);
    std::vector<std::string> cpu_outputs;
    std::vector<std::string> gpu_outputs;
    const double cpu_ms = cpu_time_ms(pts, cpu_outputs);

    GpuTimingResult timing;
    std::string error;
    bool ok_call = false;
    if (overlap)
    {
        std::vector<std::vector<PcfgGpuPtBatch>> chunks;
        for (const PcfgGpuPtBatch &pt : pts)
        {
            chunks.push_back({pt});
        }
        ok_call = gpu_generate_guesses_multi_pt_overlapped(
            chunks, gpu_outputs, nullptr, &timing, &error);
    }
    else
    {
        ok_call = gpu_generate_guesses_multi_pt(
            pts, gpu_outputs, nullptr, &timing, &error);
    }
    if (!ok_call)
    {
        std::cerr << "[error] " << error << "\n";
        return 1;
    }

    std::size_t matched = 0;
    const bool ok = compare_guess_batches(cpu_outputs, gpu_outputs, &matched);
    std::cout << std::fixed << std::setprecision(4);
    const char *tag = overlap ? "overlap" : "multi";
    if (!bench)
    {
        std::cout << "[" << tag << "-check] pts=" << options.pts
                  << " batch_per_pt=" << options.batch
                  << " matched=" << matched << "/" << cpu_outputs.size()
                  << " " << (ok ? "PASS" : "FAIL") << "\n";
        return ok ? 0 : 1;
    }

    const double speedup = timing.total_gpu_ms > 0.0f
                               ? cpu_ms / static_cast<double>(timing.total_gpu_ms)
                               : 0.0;
    std::cout << "[" << tag << "-bench] pts=" << options.pts
              << " guesses=" << cpu_outputs.size()
              << " cpu_ms=" << cpu_ms
              << " h2d_ms=" << timing.h2d_ms
              << " kernel_ms=" << timing.kernel_ms
              << " d2h_ms=" << timing.d2h_ms
              << " gpu_total_ms=" << timing.total_gpu_ms
              << " cpu_overlap_ms=" << timing.cpu_overlap_ms
              << " speedup=" << speedup
              << " correctness=" << (ok ? "PASS" : "FAIL") << "\n";
    return ok ? 0 : 1;
}

int run_schedule(const Options &options, bool bench)
{
    const std::vector<PcfgGpuPtBatch> pts = make_skewed_pt_batches(options.prefix);
    const PcfgSchedulingConfig config;
    const PcfgScheduledWork scheduled = schedule_pt_batches_for_gpu(pts, config);

    std::vector<std::string> expected;
    const double cpu_all_ms = cpu_time_ms(pts, expected);

    const auto scheduled_start = std::chrono::high_resolution_clock::now();
    std::vector<std::string> actual = cpu_generate_guesses_multi_pt(scheduled.cpu_pts);

    GpuTimingResult timing;
    std::string error;
    std::vector<std::string> gpu_outputs;
    if (!gpu_generate_guesses_multi_pt_overlapped(
            scheduled.gpu_chunks, gpu_outputs, nullptr, &timing, &error))
    {
        std::cerr << "[error] " << error << "\n";
        return 1;
    }
    actual.insert(actual.end(), gpu_outputs.begin(), gpu_outputs.end());
    const auto scheduled_stop = std::chrono::high_resolution_clock::now();
    const double scheduled_wall_ms =
        std::chrono::duration<double, std::milli>(scheduled_stop - scheduled_start).count();

    std::size_t matched = 0;
    const bool ok = compare_sorted(expected, actual, &matched);
    if (!bench)
    {
        std::cout << "[schedule] cpu_pts=" << scheduled.cpu_pts.size()
                  << " gpu_chunks=" << scheduled.gpu_chunks.size()
                  << " cpu_guesses=" << pcfg_count_values(scheduled.cpu_pts)
                  << " gpu_guesses=" << timing.gpu_guess_count
                  << " matched=" << matched << "/" << expected.size()
                  << " " << (ok ? "PASS" : "FAIL") << "\n";
        return ok ? 0 : 1;
    }

    const double speedup = scheduled_wall_ms > 0.0 ? cpu_all_ms / scheduled_wall_ms : 0.0;
    std::cout << std::fixed << std::setprecision(4);
    std::cout << "[schedule-bench] cpu_pts=" << scheduled.cpu_pts.size()
              << " gpu_chunks=" << scheduled.gpu_chunks.size()
              << " cpu_guesses=" << pcfg_count_values(scheduled.cpu_pts)
              << " gpu_guesses=" << timing.gpu_guess_count
              << " cpu_all_ms=" << cpu_all_ms
              << " scheduled_wall_ms=" << scheduled_wall_ms
              << " h2d_ms=" << timing.h2d_ms
              << " kernel_ms=" << timing.kernel_ms
              << " d2h_ms=" << timing.d2h_ms
              << " gpu_total_ms=" << timing.total_gpu_ms
              << " cpu_overlap_ms=" << timing.cpu_overlap_ms
              << " speedup=" << speedup
              << " correctness=" << (ok ? "PASS" : "FAIL") << "\n";
    return ok ? 0 : 1;
}

} // namespace

int main(int argc, char **argv)
{
    const Options options = parse_options(argc, argv);
    if (options.batch < 0 || options.pts < 1)
    {
        std::cerr << "[error] invalid --batch or --pts\n";
        return 1;
    }
    if (options.mode == "cpu")
    {
        return run_cpu(options);
    }
    if (options.mode == "check")
    {
        return run_single(options, false);
    }
    if (options.mode == "bench")
    {
        return run_single(options, true);
    }
    if (options.mode == "multi-check")
    {
        return run_multi(options, false, false);
    }
    if (options.mode == "multi-bench")
    {
        return run_multi(options, false, true);
    }
    if (options.mode == "overlap-check")
    {
        return run_multi(options, true, false);
    }
    if (options.mode == "overlap-bench")
    {
        return run_multi(options, true, true);
    }
    if (options.mode == "schedule")
    {
        return run_schedule(options, false);
    }
    if (options.mode == "schedule-bench")
    {
        return run_schedule(options, true);
    }
    std::cerr << "[error] unknown mode: " << options.mode << "\n";
    return 1;
}
