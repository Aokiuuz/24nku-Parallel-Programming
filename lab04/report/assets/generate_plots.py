import csv
import re
import statistics
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[2] / "ARM_code"
OUT = Path(__file__).resolve().parent

BLUE = "#2F5597"
ORANGE = "#C55A11"
GREEN = "#548235"
PURPLE = "#6F4E7C"
GRAY = "#6B7280"
LIGHT = "#E5E7EB"


def metric(path, name):
    text = path.read_text(errors="replace")
    matches = re.findall(r"^" + re.escape(name) + r"\s*([0-9.]+)", text, re.M)
    return float(matches[-1])


def read_suite(version, manifest_name, prefix, communication_name):
    data_dir = ROOT / version / "data"
    rows = []
    with (data_dir / manifest_name).open(encoding="utf-8-sig", newline="") as file:
        for item in csv.DictReader(file, delimiter="\t"):
            path = data_dir / prefix.format(task_id=item["task_id"])
            row = dict(item)
            row.update(
                {
                    "train": metric(path, "Train time:"),
                    "guess": metric(path, "Guess time:"),
                    "hash": metric(path, "Hash time:"),
                    "comm": metric(path, communication_name),
                    "wall": metric(path, "MPI wall time:"),
                    "processed": metric(path, "Processed guesses:"),
                }
            )
            rows.append(row)
    return rows


def group_medians(rows, key):
    result = []
    values = sorted({int(row[key]) for row in rows})
    for value in values:
        group = [row for row in rows if int(row[key]) == value]
        result.append(
            {
                key: value,
                "runs": len(group),
                "train": statistics.median(row["train"] for row in group),
                "guess": statistics.median(row["guess"] for row in group),
                "hash": statistics.median(row["hash"] for row in group),
                "comm": statistics.median(row["comm"] for row in group),
                "wall": statistics.median(row["wall"] for row in group),
                "processed": statistics.median(row["processed"] for row in group),
                "wall_min": min(row["wall"] for row in group),
                "wall_max": max(row["wall"] for row in group),
            }
        )
    return result


def style_axis(axis):
    axis.grid(True, color=LIGHT, linewidth=0.7)
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    axis.spines["left"].set_color(GRAY)
    axis.spines["bottom"].set_color(GRAY)
    axis.tick_params(colors="#1F2937")


plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 9,
        "axes.labelcolor": "#1F2937",
        "axes.titlecolor": "#1F2937",
        "figure.dpi": 160,
        "savefig.bbox": "tight",
    }
)

base_rows = read_suite(
    "guess_mpi_base",
    "experiment_manifest.tsv",
    "mpi_task_{task_id}.o",
    "MPI communication/wait time:",
)
advanced_scale_rows = read_suite(
    "guess_mpi_advanced",
    "experiment_manifest_scale.tsv",
    "scale_mpi_task_{task_id}.o",
    "MPI communication time:",
)
advanced_thread_rows = read_suite(
    "guess_mpi_advanced",
    "experiment_manifest_threads.tsv",
    "threads_mpi_task_{task_id}.o",
    "MPI communication time:",
)
advanced_batch_rows = read_suite(
    "guess_mpi_advanced",
    "experiment_manifest_batch.tsv",
    "batch_mpi_task_{task_id}.o",
    "MPI communication time:",
)

base = group_medians(base_rows, "np")
advanced_scale = group_medians(advanced_scale_rows, "np")
advanced_threads = group_medians(advanced_thread_rows, "gen_threads")
advanced_batch = group_medians(advanced_batch_rows, "batch_guesses")

base_wall_1 = base[0]["wall"]
for row in base:
    row["speedup"] = base_wall_1 / row["wall"]
    row["efficiency"] = row["speedup"] / row["np"]
    row["comm_share"] = row["comm"] / row["wall"]
for row in advanced_scale:
    row["comm_share"] = row["comm"] / row["wall"]

fig, axes = plt.subplots(1, 2, figsize=(8.8, 3.25))
axis = axes[0]
x = [row["np"] for row in base]
y = [row["wall"] for row in base]
low = [row["wall"] - row["wall_min"] for row in base]
high = [row["wall_max"] - row["wall"] for row in base]
axis.errorbar(x, y, yerr=[low, high], color=BLUE, marker="o", capsize=3, linewidth=1.8)
axis.set_xscale("log", base=2)
axis.set_xticks(x, labels=x)
axis.set_xlabel("MPI processes")
axis.set_ylabel("MPI wall time (s)")
axis.set_title("Base: parallel-stage wall time")
style_axis(axis)

axis = axes[1]
axis.plot(x, [row["speedup"] for row in base], color=ORANGE, marker="o", label="Speedup")
axis.plot(x, [row["efficiency"] for row in base], color=GREEN, marker="s", label="Efficiency")
axis.plot(x, x, color=GRAY, linestyle="--", linewidth=1, label="Ideal speedup")
axis.set_xscale("log", base=2)
axis.set_xticks(x, labels=x)
axis.set_xlabel("MPI processes")
axis.set_ylabel("Ratio")
axis.set_title("Base: speedup and efficiency")
axis.legend(frameon=False)
style_axis(axis)
fig.tight_layout()
fig.savefig(OUT / "base_scaling.pdf")
plt.close(fig)

common = [2, 4, 8, 16]
base_common = {row["np"]: row for row in base}
advanced_common = {row["np"]: row for row in advanced_scale}
fig, axes = plt.subplots(1, 2, figsize=(8.8, 3.25))
axis = axes[0]
positions = np.arange(len(common))
width = 0.34
axis.bar(positions - width / 2, [base_common[n]["wall"] for n in common], width, color=BLUE, label="Base")
axis.bar(positions + width / 2, [advanced_common[n]["wall"] for n in common], width, color=ORANGE, label="Advanced")
axis.set_xticks(positions, labels=common)
axis.set_xlabel("MPI processes")
axis.set_ylabel("MPI wall time (s)")
axis.set_title("Blocking tasks vs. pipeline batches")
axis.legend(frameon=False)
style_axis(axis)

axis = axes[1]
axis.plot(common, [100 * base_common[n]["comm_share"] for n in common], color=BLUE, marker="o", label="Base")
axis.plot(common, [100 * advanced_common[n]["comm_share"] for n in common], color=ORANGE, marker="s", label="Advanced")
axis.set_xscale("log", base=2)
axis.set_xticks(common, labels=common)
axis.set_xlabel("MPI processes")
axis.set_ylabel("Communication share (%)")
axis.set_title("Communication in MPI wall time")
axis.legend(frameon=False)
style_axis(axis)
fig.tight_layout()
fig.savefig(OUT / "version_compare.pdf")
plt.close(fig)

fig, axes = plt.subplots(1, 2, figsize=(8.8, 3.25))
axis = axes[0]
x = [row["gen_threads"] for row in advanced_threads]
axis.plot(x, [row["wall"] for row in advanced_threads], color=PURPLE, marker="o", label="MPI wall")
axis.plot(x, [row["guess"] for row in advanced_threads], color=GREEN, marker="s", label="Generate critical path")
axis.set_xticks(x)
axis.set_xlabel("Generator threads")
axis.set_ylabel("Time (s)")
axis.set_title("Advanced: generator-thread tuning")
axis.legend(frameon=False)
style_axis(axis)

axis = axes[1]
x = [row["batch_guesses"] for row in advanced_batch]
axis.plot(x, [row["wall"] for row in advanced_batch], color=ORANGE, marker="o", label="MPI wall")
axis.plot(x, [row["comm"] for row in advanced_batch], color=BLUE, marker="s", label="Communication")
axis.set_xscale("log")
axis.set_xticks(x, labels=["10k", "50k", "100k", "500k"])
axis.set_xlabel("Batch guesses")
axis.set_ylabel("Time (s)")
axis.set_title("Advanced: batch-size tuning")
axis.legend(frameon=False)
style_axis(axis)
fig.tight_layout()
fig.savefig(OUT / "advanced_tuning.pdf")
plt.close(fig)

backup_dir = ROOT / "guess_mpi_backup" / "data"
backup_rows = []
with (backup_dir / "experiment_manifest.tsv").open(encoding="utf-8-sig", newline="") as file:
    for item in csv.DictReader(file, delimiter="\t"):
        path = backup_dir / f"mpi_task_{item['task_id']}.o"
        backup_rows.append({"mode": item["mode"], "hash": metric(path, "Hash time:")})
backup_hash = {
    mode: statistics.median(row["hash"] for row in backup_rows if row["mode"] == mode)
    for mode in ("serial", "simd")
}
fig, axis = plt.subplots(figsize=(5.3, 3.2))
bars = axis.bar(["Serial MD5", "NEON SIMD MD5"], [backup_hash["serial"], backup_hash["simd"]], color=[GRAY, GREEN])
axis.bar_label(bars, labels=[f"{backup_hash['serial']:.3f}s", f"{backup_hash['simd']:.3f}s"], padding=3)
axis.text(0.5, max(backup_hash.values()) * 0.82, f"{backup_hash['serial'] / backup_hash['simd']:.2f}x hash speedup", ha="center", color=GREEN, fontweight="bold")
axis.set_ylabel("Hash time (s)")
axis.set_title("Single-process MD5 implementation")
style_axis(axis)
fig.tight_layout()
fig.savefig(OUT / "simd_hash.pdf")
plt.close(fig)

size_1m_path = ROOT / "guess_mpi_advanced" / "data" / "scale_size_1m.o"
size_1m = {
    "processed": metric(size_1m_path, "Processed guesses:"),
    "wall": metric(size_1m_path, "MPI wall time:"),
    "comm": metric(size_1m_path, "MPI communication time:"),
}
size_10m = next(row for row in advanced_scale if row["np"] == 4)
fig, axes = plt.subplots(1, 2, figsize=(8.8, 3.25))
axis = axes[0]
bars = axis.bar(["1M target", "10M target"], [size_1m["wall"], size_10m["wall"]], color=[BLUE, ORANGE])
axis.bar_label(bars, labels=[f"{size_1m['wall']:.3f}s", f"{size_10m['wall']:.3f}s"], padding=3)
axis.set_ylabel("MPI wall time (s)")
axis.set_title("Advanced NP=4: problem size")
style_axis(axis)
axis = axes[1]
throughputs = [
    size_1m["processed"] / size_1m["wall"] / 1e6,
    size_10m["processed"] / size_10m["wall"] / 1e6,
]
bars = axis.bar(["1M target", "10M target"], throughputs, color=[BLUE, ORANGE])
axis.bar_label(bars, labels=[f"{value:.2f}M/s" for value in throughputs], padding=3)
axis.set_ylabel("Throughput (million guesses/s)")
axis.set_title("Advanced NP=4: effective throughput")
style_axis(axis)
fig.tight_layout()
fig.savefig(OUT / "problem_size.pdf")
plt.close(fig)

summary_rows = []
for row in base:
    summary_rows.append({"suite": "base_scale", **row})
for row in advanced_scale:
    summary_rows.append({"suite": "advanced_scale", **row})
for row in advanced_threads:
    summary_rows.append({"suite": "advanced_threads", **row})
for row in advanced_batch:
    summary_rows.append({"suite": "advanced_batch", **row})

fieldnames = sorted({key for row in summary_rows for key in row})
with (OUT / "results_summary.csv").open("w", encoding="utf-8", newline="") as file:
    writer = csv.DictWriter(file, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(summary_rows)

print("generated figures and results_summary.csv")
