#include "PCFG.h"
#include "pcfg_gpu_generate.h"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

using Clock = std::chrono::steady_clock;

namespace
{

struct Options
{
    std::string train_path = "/guessdata/Rockyou-singleLined-full.txt";
    std::vector<uint64_t> limits = {10000, 100000, 1000000};
    int repeats = 5;
    std::size_t pts_per_batch = 4;
};

struct PreparedUnit
{
    WorkUnit unit;
    PcfgGpuPtBatch batch;
    bool gpu_eligible = false;
};

struct RunResult
{
    std::vector<std::string> outputs;
    GpuTimingResult gpu;
    double wall_ms = 0.0;
    double host_prepare_ms = 0.0;
    std::size_t gpu_units = 0;
    std::size_t cpu_fallback_units = 0;
    uint64_t gpu_guesses = 0;
    uint64_t cpu_fallback_guesses = 0;
    std::size_t input_units = 0;
};

static double elapsed_ms(Clock::time_point start, Clock::time_point stop)
{
    return std::chrono::duration<double, std::milli>(stop - start).count();
}

static std::vector<uint64_t> parse_limits(const std::string &text)
{
    std::vector<uint64_t> values;
    std::stringstream input(text);
    std::string part;
    while (std::getline(input, part, ','))
    {
        if (!part.empty())
        {
            values.push_back(static_cast<uint64_t>(std::stoull(part)));
        }
    }
    if (values.empty())
    {
        throw std::runtime_error("--limits must contain at least one positive integer");
    }
    for (uint64_t value : values)
    {
        if (value == 0)
        {
            throw std::runtime_error("--limits values must be positive");
        }
    }
    std::sort(values.begin(), values.end());
    values.erase(std::unique(values.begin(), values.end()), values.end());
    return values;
}

static Options parse_options(int argc, char **argv)
{
    Options options;
    for (int i = 1; i < argc; i += 1)
    {
        const std::string arg = argv[i];
        if (arg == "--train" && i + 1 < argc)
        {
            options.train_path = argv[++i];
        }
        else if (arg == "--limits" && i + 1 < argc)
        {
            options.limits = parse_limits(argv[++i]);
        }
        else if (arg == "--repeats" && i + 1 < argc)
        {
            options.repeats = std::max(1, std::stoi(argv[++i]));
        }
        else if (arg == "--pts-per-batch" && i + 1 < argc)
        {
            options.pts_per_batch = std::max<std::size_t>(1, std::stoull(argv[++i]));
        }
        else if (arg == "--help")
        {
            std::cout
                << "Usage: pcfg_real_gpu_test [options]\n"
                << "  --train PATH             training password file\n"
                << "  --limits A,B,C           generated guess limits\n"
                << "  --repeats N              repetitions per mode and scale\n"
                << "  --pts-per-batch N        fixed PT count for multi/overlap\n";
            std::exit(0);
        }
        else
        {
            throw std::runtime_error("unknown or incomplete option: " + arg);
        }
    }
    return options;
}

static segment *find_last_segment(PriorityQueue &queue, const PT &pt)
{
    const segment &last = pt.content.back();
    if (last.type == 1)
    {
        return &queue.m.letters[queue.m.FindLetter(last)];
    }
    if (last.type == 2)
    {
        return &queue.m.digits[queue.m.FindDigit(last)];
    }
    return &queue.m.symbols[queue.m.FindSymbol(last)];
}

static std::string build_prefix(PriorityQueue &queue, const PT &pt)
{
    std::string prefix;
    for (std::size_t seg_idx = 0; seg_idx + 1 < pt.content.size(); seg_idx += 1)
    {
        const int value_idx = pt.curr_indices[seg_idx];
        const segment &seg = pt.content[seg_idx];
        if (seg.type == 1)
        {
            prefix += queue.m.letters[queue.m.FindLetter(seg)].ordered_values[value_idx];
        }
        else if (seg.type == 2)
        {
            prefix += queue.m.digits[queue.m.FindDigit(seg)].ordered_values[value_idx];
        }
        else
        {
            prefix += queue.m.symbols[queue.m.FindSymbol(seg)].ordered_values[value_idx];
        }
    }
    return prefix;
}

static PreparedUnit prepare_unit(PriorityQueue &queue, const WorkUnit &unit)
{
    PreparedUnit prepared;
    prepared.unit = unit;
    if (unit.pt.content.empty())
    {
        return prepared;
    }

    prepared.batch.prefix = build_prefix(queue, unit.pt);
    segment *last = find_last_segment(queue, unit.pt);
    const uint64_t count = queue.GuessCount(unit.pt);
    const uint64_t begin = std::min(unit.begin, count);
    const uint64_t end = std::min(unit.end, count);
    prepared.batch.values.reserve(static_cast<std::size_t>(end - begin));
    prepared.gpu_eligible =
        prepared.batch.prefix.size() <= static_cast<std::size_t>(PCFG_GPU_MAX_GUESS_LEN);

    for (uint64_t i = begin; i < end; i += 1)
    {
        const std::string &value = last->ordered_values[static_cast<std::size_t>(i)];
        prepared.batch.values.push_back(value);
        if (value.size() > static_cast<std::size_t>(PCFG_GPU_MAX_VALUE_LEN) ||
            prepared.batch.prefix.size() + value.size() >
                static_cast<std::size_t>(PCFG_GPU_MAX_GUESS_LEN))
        {
            prepared.gpu_eligible = false;
        }
    }
    return prepared;
}

static uint64_t fnv1a_hash(const std::vector<std::string> &items)
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

static void merge_timing(GpuTimingResult &dst, const GpuTimingResult &src)
{
    dst.host_pack_ms += src.host_pack_ms;
    dst.host_unpack_ms += src.host_unpack_ms;
    dst.h2d_ms += src.h2d_ms;
    dst.kernel_ms += src.kernel_ms;
    dst.d2h_ms += src.d2h_ms;
    dst.total_gpu_ms += src.total_gpu_ms;
    dst.cpu_overlap_ms += src.cpu_overlap_ms;
    dst.gpu_pt_count += src.gpu_pt_count;
    dst.gpu_guess_count += src.gpu_guess_count;
    dst.cpu_pt_count += src.cpu_pt_count;
    dst.cpu_guess_count += src.cpu_guess_count;
}

static std::vector<WorkUnit> collect_units(PriorityQueue &queue, uint64_t limit)
{
    std::vector<WorkUnit> units;
    uint64_t collected = 0;
    while (collected < limit && !queue.priority.empty())
    {
        PT pt = queue.PopNextTask();
        const uint64_t count = queue.GuessCount(pt);
        if (count == 0)
        {
            continue;
        }
        const uint64_t take = std::min(count, limit - collected);
        WorkUnit unit;
        unit.pt = std::move(pt);
        unit.begin = 0;
        unit.end = take;
        units.push_back(std::move(unit));
        collected += take;
    }
    return units;
}

static std::vector<WorkUnit> slice_units(const std::vector<WorkUnit> &source,
                                         uint64_t limit)
{
    std::vector<WorkUnit> sliced;
    uint64_t count = 0;
    for (const WorkUnit &unit : source)
    {
        if (count >= limit)
        {
            break;
        }
        WorkUnit piece = unit;
        const uint64_t available = unit.end - unit.begin;
        const uint64_t take = std::min(available, limit - count);
        piece.end = piece.begin + take;
        sliced.push_back(std::move(piece));
        count += take;
    }
    return sliced;
}

static RunResult run_cpu(PriorityQueue &queue, const std::vector<WorkUnit> &units)
{
    RunResult result;
    result.input_units = units.size();
    const auto start = Clock::now();
    for (const WorkUnit &unit : units)
    {
        queue.GenerateRange(unit, result.outputs);
    }
    result.wall_ms = elapsed_ms(start, Clock::now());
    result.cpu_fallback_units = units.size();
    result.cpu_fallback_guesses = result.outputs.size();
    return result;
}

static void append_cpu_unit(PriorityQueue &queue, const WorkUnit &unit,
                            RunResult &result)
{
    const std::size_t before = result.outputs.size();
    queue.GenerateRange(unit, result.outputs);
    result.cpu_fallback_units += 1;
    result.cpu_fallback_guesses += result.outputs.size() - before;
}

static bool run_gpu_group(const std::vector<PcfgGpuPtBatch> &batches,
                          RunResult &result, std::string &error)
{
    std::vector<std::string> outputs;
    GpuTimingResult timing;
    if (!gpu_generate_guesses_multi_pt(batches, outputs, nullptr, &timing, &error))
    {
        return false;
    }
    result.outputs.insert(result.outputs.end(), outputs.begin(), outputs.end());
    result.gpu_units += batches.size();
    result.gpu_guesses += outputs.size();
    merge_timing(result.gpu, timing);
    return true;
}

static RunResult run_grouped(PriorityQueue &queue, const std::vector<WorkUnit> &units,
                             std::size_t group_size, bool overlap,
                             std::string &error)
{
    RunResult result;
    result.input_units = units.size();
    const auto wall_start = Clock::now();
    const auto prepare_start = Clock::now();
    std::vector<PreparedUnit> prepared;
    prepared.reserve(units.size());
    for (const WorkUnit &unit : units)
    {
        prepared.push_back(prepare_unit(queue, unit));
    }
    result.host_prepare_ms = elapsed_ms(prepare_start, Clock::now());

    if (!overlap)
    {
        std::vector<PcfgGpuPtBatch> group;
        auto flush = [&]() -> bool {
            if (group.empty()) return true;
            const bool ok = run_gpu_group(group, result, error);
            group.clear();
            return ok;
        };

        for (const PreparedUnit &item : prepared)
        {
            if (!item.gpu_eligible)
            {
                if (!flush()) return result;
                append_cpu_unit(queue, item.unit, result);
                continue;
            }
            group.push_back(item.batch);
            if (group.size() >= group_size && !flush()) return result;
        }
        flush();
    }
    else
    {
        std::vector<std::vector<PcfgGpuPtBatch>> pending_chunks;
        std::vector<PcfgGpuPtBatch> current;
        auto flush_overlap = [&]() -> bool {
            if (!current.empty())
            {
                pending_chunks.push_back(current);
                current.clear();
            }
            if (pending_chunks.empty()) return true;
            std::vector<std::string> outputs;
            GpuTimingResult timing;
            if (!gpu_generate_guesses_multi_pt_overlapped(
                    pending_chunks, outputs, nullptr, &timing, &error))
            {
                return false;
            }
            for (const auto &chunk : pending_chunks) result.gpu_units += chunk.size();
            result.gpu_guesses += outputs.size();
            result.outputs.insert(result.outputs.end(), outputs.begin(), outputs.end());
            merge_timing(result.gpu, timing);
            pending_chunks.clear();
            return true;
        };

        for (const PreparedUnit &item : prepared)
        {
            if (!item.gpu_eligible)
            {
                if (!flush_overlap()) return result;
                append_cpu_unit(queue, item.unit, result);
                continue;
            }
            current.push_back(item.batch);
            if (current.size() >= group_size)
            {
                pending_chunks.push_back(current);
                current.clear();
            }
        }
        flush_overlap();
    }

    result.wall_ms = elapsed_ms(wall_start, Clock::now());
    return result;
}

static RunResult run_scheduled(PriorityQueue &queue,
                               const std::vector<WorkUnit> &units,
                               const PcfgSchedulingConfig &config,
                               std::string &error)
{
    RunResult result;
    result.input_units = units.size();
    const auto wall_start = Clock::now();
    const auto prepare_start = Clock::now();
    std::vector<PcfgGpuPtBatch> eligible;
    std::vector<WorkUnit> unsupported;
    for (const WorkUnit &unit : units)
    {
        PreparedUnit item = prepare_unit(queue, unit);
        if (item.gpu_eligible)
        {
            eligible.push_back(std::move(item.batch));
        }
        else
        {
            unsupported.push_back(unit);
        }
    }
    result.host_prepare_ms = elapsed_ms(prepare_start, Clock::now());

    const PcfgScheduledWork scheduled = schedule_pt_batches_for_gpu(eligible, config);
    result.outputs = cpu_generate_guesses_multi_pt(scheduled.cpu_pts);
    result.cpu_fallback_units = scheduled.cpu_pts.size();
    result.cpu_fallback_guesses = result.outputs.size();
    for (const WorkUnit &unit : unsupported)
    {
        append_cpu_unit(queue, unit, result);
    }

    std::vector<std::string> gpu_outputs;
    GpuTimingResult timing;
    if (!gpu_generate_guesses_multi_pt_overlapped(
            scheduled.gpu_chunks, gpu_outputs, nullptr, &timing, &error))
    {
        return result;
    }
    for (const auto &chunk : scheduled.gpu_chunks) result.gpu_units += chunk.size();
    result.gpu_guesses = gpu_outputs.size();
    result.outputs.insert(result.outputs.end(), gpu_outputs.begin(), gpu_outputs.end());
    merge_timing(result.gpu, timing);
    result.wall_ms = elapsed_ms(wall_start, Clock::now());
    return result;
}

static bool compare_sorted(std::vector<std::string> expected,
                           std::vector<std::string> actual)
{
    std::sort(expected.begin(), expected.end());
    std::sort(actual.begin(), actual.end());
    return expected == actual;
}

static double percentile(std::vector<uint64_t> values, double q)
{
    if (values.empty()) return 0.0;
    std::sort(values.begin(), values.end());
    const double position = q * static_cast<double>(values.size() - 1);
    const std::size_t lo = static_cast<std::size_t>(std::floor(position));
    const std::size_t hi = static_cast<std::size_t>(std::ceil(position));
    const double fraction = position - static_cast<double>(lo);
    return static_cast<double>(values[lo]) * (1.0 - fraction) +
           static_cast<double>(values[hi]) * fraction;
}

static void print_pt_stats(const std::vector<WorkUnit> &units, uint64_t limit)
{
    std::vector<uint64_t> counts;
    counts.reserve(units.size());
    for (const WorkUnit &unit : units) counts.push_back(unit.end - unit.begin);
    const uint64_t total = std::accumulate(counts.begin(), counts.end(), uint64_t{0});
    const auto minmax = std::minmax_element(counts.begin(), counts.end());
    std::cout << "[real-pt-stats] limit=" << limit
              << " units=" << counts.size()
              << " guesses=" << total
              << " min=" << (counts.empty() ? 0 : *minmax.first)
              << " p50=" << percentile(counts, 0.50)
              << " p90=" << percentile(counts, 0.90)
              << " p99=" << percentile(counts, 0.99)
              << " max=" << (counts.empty() ? 0 : *minmax.second) << "\n";
}

static void print_result(const std::string &mode, uint64_t limit, int repeat,
                         const RunResult &result,
                         const std::vector<std::string> &expected,
                         bool sorted_compare,
                         double cpu_baseline_ms)
{
    const bool count_ok = result.outputs.size() == expected.size();
    std::vector<std::string> hash_actual = result.outputs;
    std::vector<std::string> hash_expected = expected;
    if (sorted_compare)
    {
        std::sort(hash_actual.begin(), hash_actual.end());
        std::sort(hash_expected.begin(), hash_expected.end());
    }
    const uint64_t actual_hash = fnv1a_hash(hash_actual);
    const uint64_t expected_hash = fnv1a_hash(hash_expected);
    const bool exact_ok = sorted_compare
                              ? compare_sorted(expected, result.outputs)
                              : result.outputs == expected;
    const bool ok = count_ok && exact_ok;
    const double speedup = result.wall_ms > 0.0
                               ? cpu_baseline_ms / result.wall_ms
                               : 0.0;
    std::cout << std::fixed << std::setprecision(4)
              << "[real-bench] mode=" << mode
              << " limit=" << limit
              << " repeat=" << repeat
              << " wall_ms=" << result.wall_ms
              << " host_prepare_ms=" << result.host_prepare_ms
              << " host_pack_ms=" << result.gpu.host_pack_ms
              << " host_unpack_ms=" << result.gpu.host_unpack_ms
              << " h2d_ms=" << result.gpu.h2d_ms
              << " kernel_ms=" << result.gpu.kernel_ms
              << " d2h_ms=" << result.gpu.d2h_ms
              << " gpu_total_ms=" << result.gpu.total_gpu_ms
              << " cpu_overlap_ms=" << result.gpu.cpu_overlap_ms
              << " input_units=" << result.input_units
              << " gpu_units=" << result.gpu_units
              << " cpu_fallback_units=" << result.cpu_fallback_units
              << " gpu_guesses=" << result.gpu_guesses
              << " cpu_fallback_guesses=" << result.cpu_fallback_guesses
              << " count=" << result.outputs.size()
              << " hash=" << actual_hash
              << " expected_hash=" << expected_hash
              << " speedup=" << speedup
              << " compare=" << (sorted_compare ? "sorted" : "ordered")
              << " correctness=" << (ok ? "PASS" : "FAIL") << "\n";
}

} // namespace

int main(int argc, char **argv)
{
    try
    {
        const Options options = parse_options(argc, argv);
        std::ifstream train_file(options.train_path);
        if (!train_file.good())
        {
            std::cerr << "[error] training file is not readable: "
                      << options.train_path << "\n";
            return 2;
        }

        PriorityQueue queue;
        const auto train_start = Clock::now();
        queue.m.train(options.train_path);
        queue.m.order();
        queue.init();
        const double train_ms = elapsed_ms(train_start, Clock::now());
        if (queue.priority.empty())
        {
            std::cerr << "[error] training produced an empty priority queue\n";
            return 3;
        }

        const uint64_t max_limit = options.limits.back();
        const auto collect_start = Clock::now();
        const std::vector<WorkUnit> all_units = collect_units(queue, max_limit);
        const double collect_ms = elapsed_ms(collect_start, Clock::now());
        const uint64_t collected = std::accumulate(
            all_units.begin(), all_units.end(), uint64_t{0},
            [](uint64_t sum, const WorkUnit &unit) {
                return sum + (unit.end - unit.begin);
            });
        if (collected < max_limit)
        {
            std::cerr << "[error] model produced only " << collected
                      << " guesses, below requested " << max_limit << "\n";
            return 4;
        }

        std::cout << std::fixed << std::setprecision(4)
                  << "[real-meta] train_path=" << options.train_path
                  << " train_ms=" << train_ms
                  << " trained_passwords=" << queue.m.trained_passwords
                  << " collect_ms=" << collect_ms
                  << " model_pts=" << queue.m.ordered_pts.size()
                  << " collected_units=" << all_units.size()
                  << " collected_guesses=" << collected
                  << " repeats=" << options.repeats
                  << " pts_per_batch=" << options.pts_per_batch << "\n";

        {
            const std::vector<std::string> warm_values = {"warmup0", "warmup1"};
            std::vector<std::string> warm_outputs;
            std::string warm_error;
            const bool warm_ok = gpu_generate_guesses(
                "pcfg_", warm_values, warm_outputs, nullptr, &warm_error);
            if (!warm_ok || warm_outputs != cpu_generate_guesses("pcfg_", warm_values))
            {
                throw std::runtime_error(
                    warm_error.empty() ? "GPU warm-up correctness failed" : warm_error);
            }
            std::cout << "[real-warmup] guesses=" << warm_outputs.size()
                      << " correctness=PASS\n";
        }

        const PcfgSchedulingConfig default_schedule;
        PcfgSchedulingConfig conservative_schedule;
        conservative_schedule.min_gpu_values = 131072;
        conservative_schedule.target_gpu_values = 262144;
        conservative_schedule.max_gpu_values = 524288;

        for (uint64_t limit : options.limits)
        {
            const std::vector<WorkUnit> units = slice_units(all_units, limit);
            print_pt_stats(units, limit);

            std::vector<std::string> expected;
            for (int repeat = 1; repeat <= options.repeats; repeat += 1)
            {
                RunResult cpu = run_cpu(queue, units);
                if (repeat == 1) expected = cpu.outputs;
                print_result("cpu", limit, repeat, cpu, expected, false,
                             cpu.wall_ms);

                std::string error;
                RunResult single = run_grouped(queue, units, 1, false, error);
                if (!error.empty()) throw std::runtime_error(error);
                print_result("single", limit, repeat, single, expected, false,
                             cpu.wall_ms);

                RunResult multi = run_grouped(
                    queue, units, options.pts_per_batch, false, error);
                if (!error.empty()) throw std::runtime_error(error);
                print_result("multi4", limit, repeat, multi, expected, false,
                             cpu.wall_ms);

                RunResult overlap = run_grouped(
                    queue, units, options.pts_per_batch, true, error);
                if (!error.empty()) throw std::runtime_error(error);
                print_result("overlap4", limit, repeat, overlap, expected, false,
                             cpu.wall_ms);

                RunResult schedule_default = run_scheduled(
                    queue, units, default_schedule, error);
                if (!error.empty()) throw std::runtime_error(error);
                print_result("schedule_default", limit, repeat,
                             schedule_default, expected, true, cpu.wall_ms);

                RunResult schedule_conservative = run_scheduled(
                    queue, units, conservative_schedule, error);
                if (!error.empty()) throw std::runtime_error(error);
                print_result("schedule_conservative", limit, repeat,
                             schedule_conservative, expected, true, cpu.wall_ms);
            }
        }
        return 0;
    }
    catch (const std::exception &error)
    {
        std::cerr << "[error] " << error.what() << "\n";
        return 1;
    }
}
