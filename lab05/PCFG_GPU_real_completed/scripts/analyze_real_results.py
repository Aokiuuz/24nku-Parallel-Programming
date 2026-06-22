#!/usr/bin/env python3
"""Parse and validate the real-PCFG benchmark output."""

from __future__ import annotations

import argparse
import csv
import math
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path


EXPECTED_LIMITS = (10_000, 100_000, 1_000_000)
EXPECTED_MODES = (
    "cpu",
    "single",
    "multi4",
    "overlap4",
    "schedule_default",
    "schedule_conservative",
)
EXPECTED_REPEATS = 5
INTEGER_FIELDS = {
    "limit",
    "repeat",
    "input_units",
    "gpu_units",
    "cpu_fallback_units",
    "gpu_guesses",
    "cpu_fallback_guesses",
    "count",
    "hash",
    "expected_hash",
}
FLOAT_FIELDS = {
    "wall_ms",
    "host_prepare_ms",
    "host_pack_ms",
    "host_unpack_ms",
    "h2d_ms",
    "kernel_ms",
    "d2h_ms",
    "gpu_total_ms",
    "cpu_overlap_ms",
    "speedup",
}
SUMMARY_FIELDS = (
    "wall_ms",
    "host_prepare_ms",
    "host_pack_ms",
    "host_unpack_ms",
    "h2d_ms",
    "kernel_ms",
    "d2h_ms",
    "gpu_total_ms",
    "cpu_overlap_ms",
    "speedup",
    "input_units",
    "gpu_units",
    "cpu_fallback_units",
    "gpu_guesses",
    "cpu_fallback_guesses",
)


def parse_key_values(line: str) -> dict[str, str]:
    return dict(re.findall(r"([A-Za-z_][A-Za-z0-9_]*)=([^\s]+)", line))


def coerce_bench(raw: dict[str, str]) -> dict[str, object]:
    row: dict[str, object] = dict(raw)
    for key in INTEGER_FIELDS:
        row[key] = int(raw[key])
    for key in FLOAT_FIELDS:
        row[key] = float(raw[key])
    return row


def parse_log(path: Path) -> tuple[list[dict[str, object]], list[dict[str, str]], list[dict[str, str]]]:
    benches: list[dict[str, object]] = []
    pt_stats: list[dict[str, str]] = []
    metadata: list[dict[str, str]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("[real-bench]"):
            benches.append(coerce_bench(parse_key_values(line)))
        elif line.startswith("[real-pt-stats]"):
            pt_stats.append(parse_key_values(line))
        elif line.startswith("[real-meta]"):
            metadata.append(parse_key_values(line))
    return benches, pt_stats, metadata


def write_rows(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def validate(rows: list[dict[str, object]], pt_stats: list[dict[str, str]], metadata: list[dict[str, str]]) -> list[str]:
    failures: list[str] = []
    expected_total = len(EXPECTED_LIMITS) * len(EXPECTED_MODES) * EXPECTED_REPEATS
    if len(rows) != expected_total:
        failures.append(f"benchmark rows: expected {expected_total}, found {len(rows)}")
    if len(metadata) != 1:
        failures.append(f"metadata rows: expected 1, found {len(metadata)}")

    stats_limits = {int(row["limit"]) for row in pt_stats if "limit" in row}
    if stats_limits != set(EXPECTED_LIMITS):
        failures.append(f"PT statistics limits: expected {EXPECTED_LIMITS}, found {sorted(stats_limits)}")

    grouped: dict[tuple[int, str], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        limit = int(row["limit"])
        mode = str(row["mode"])
        grouped[(limit, mode)].append(row)
        if limit not in EXPECTED_LIMITS:
            failures.append(f"unexpected limit {limit}")
        if mode not in EXPECTED_MODES:
            failures.append(f"unexpected mode {mode}")
        if row.get("correctness") != "PASS":
            failures.append(f"correctness failure: limit={limit} mode={mode} repeat={row['repeat']}")
        if int(row["count"]) != limit:
            failures.append(f"count mismatch: limit={limit} mode={mode} repeat={row['repeat']}")
        if int(row["hash"]) != int(row["expected_hash"]):
            failures.append(f"hash mismatch: limit={limit} mode={mode} repeat={row['repeat']}")
        routed = int(row["gpu_guesses"]) + int(row["cpu_fallback_guesses"])
        if routed != limit:
            failures.append(
                f"routing conservation failure: limit={limit} mode={mode} "
                f"repeat={row['repeat']} routed={routed}"
            )
        for field in FLOAT_FIELDS:
            value = float(row[field])
            if not math.isfinite(value) or value < 0:
                failures.append(
                    f"invalid {field}: limit={limit} mode={mode} repeat={row['repeat']} value={value}"
                )

    for limit in EXPECTED_LIMITS:
        for mode in EXPECTED_MODES:
            group = grouped.get((limit, mode), [])
            repeats = sorted(int(row["repeat"]) for row in group)
            if repeats != list(range(1, EXPECTED_REPEATS + 1)):
                failures.append(
                    f"repeat set mismatch: limit={limit} mode={mode} repeats={repeats}"
                )

    for limit in EXPECTED_LIMITS:
        baseline_hashes = {
            int(row["hash"]) for row in grouped.get((limit, "cpu"), [])
        }
        if len(baseline_hashes) != 1:
            failures.append(f"CPU baseline hash is unstable at limit={limit}")
    return failures


def summarize(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[int, str], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[(int(row["limit"]), str(row["mode"]))].append(row)

    summary: list[dict[str, object]] = []
    for limit in EXPECTED_LIMITS:
        for mode in EXPECTED_MODES:
            group = grouped.get((limit, mode), [])
            if not group:
                continue
            item: dict[str, object] = {"limit": limit, "mode": mode, "n": len(group)}
            for field in SUMMARY_FIELDS:
                values = [float(row[field]) for row in group]
                item[f"{field}_mean"] = statistics.fmean(values)
                item[f"{field}_std"] = statistics.stdev(values) if len(values) > 1 else 0.0
            summary.append(item)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path, help="real_raw.txt produced by the benchmark")
    parser.add_argument("--output-dir", type=Path, default=Path("results"))
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows, pt_stats, metadata = parse_log(args.input)
    failures = validate(rows, pt_stats, metadata)

    raw_fields = [
        "mode", "limit", "repeat", "wall_ms", "host_prepare_ms", "host_pack_ms",
        "host_unpack_ms", "h2d_ms", "kernel_ms", "d2h_ms", "gpu_total_ms",
        "cpu_overlap_ms", "input_units", "gpu_units", "cpu_fallback_units",
        "gpu_guesses", "cpu_fallback_guesses", "count", "hash", "expected_hash",
        "speedup", "compare", "correctness",
    ]
    write_rows(args.output_dir / "real_raw.csv", rows, raw_fields)

    summary = summarize(rows)
    summary_fields = ["limit", "mode", "n"] + [
        f"{field}_{suffix}"
        for field in SUMMARY_FIELDS
        for suffix in ("mean", "std")
    ]
    write_rows(args.output_dir / "real_summary.csv", summary, summary_fields)

    stats_fields = ["limit", "units", "guesses", "min", "p50", "p90", "p99", "max"]
    write_rows(args.output_dir / "real_pt_stats.csv", pt_stats, stats_fields)
    if metadata:
        write_rows(args.output_dir / "real_metadata.csv", metadata, list(metadata[0].keys()))

    status = "PASS" if not failures else "FAIL"
    validation_lines = [
        f"status={status}",
        f"benchmark_rows={len(rows)}",
        f"expected_rows={len(EXPECTED_LIMITS) * len(EXPECTED_MODES) * EXPECTED_REPEATS}",
        f"pt_stats_rows={len(pt_stats)}",
        f"failures={len(failures)}",
    ]
    validation_lines.extend(f"failure={failure}" for failure in failures)
    (args.output_dir / "real_validation.txt").write_text(
        "\n".join(validation_lines) + "\n", encoding="utf-8"
    )
    print("\n".join(validation_lines))
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
