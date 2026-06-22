#!/usr/bin/env python3
"""Validate Lab5 evidence and generate report-ready figures.

The experiment artifacts are treated as immutable inputs.  All generated files
are written below report/figures/ in both PNG (visual QA) and PDF (XeLaTeX).
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib import font_manager as fm
import numpy as np
import pandas as pd
import seaborn as sns


REPORT_DIR = Path(__file__).resolve().parent
ROOT = REPORT_DIR.parent
OUT_DIR = REPORT_DIR / "figures"
CJK_FONT_PATH = Path("C:/Windows/Fonts/msyh.ttc")
CJK_FONT_PROP = fm.FontProperties(fname=CJK_FONT_PATH) if CJK_FONT_PATH.exists() else fm.FontProperties(family="sans-serif")

TOKENS = {
    "surface": "#FCFCFD",
    "panel": "#FFFFFF",
    "ink": "#1F2430",
    "muted": "#6F768A",
    "grid": "#E6E8F0",
    "axis": "#D7DBE7",
}
COLORS = {
    "blue": {"xlight": "#EAF1FE", "light": "#CEDFFE", "base": "#A3BEFA", "mid": "#5477C4", "dark": "#2E4780"},
    "gold": {"xlight": "#FFF4C2", "light": "#FFEA8F", "base": "#FFE15B", "mid": "#B8A037", "dark": "#736422"},
    "orange": {"xlight": "#FFEDDE", "light": "#FFBDA1", "base": "#F0986E", "mid": "#CC6F47", "dark": "#804126"},
    "olive": {"xlight": "#D8ECBD", "light": "#BEEB96", "base": "#A3D576", "mid": "#71B436", "dark": "#386411"},
    "pink": {"xlight": "#FCDAD6", "light": "#F5BACC", "base": "#F390CA", "mid": "#BD569B", "dark": "#8A3A6F"},
}
NEUTRAL = {"xlight": "#F4F5F7", "light": "#E2E5EA", "base": "#C5CAD3", "mid": "#7A828F", "dark": "#464C55"}


def use_chart_theme() -> None:
    if CJK_FONT_PATH.exists():
        fm.fontManager.addfont(CJK_FONT_PATH)
    mpl.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["DejaVu Sans", "Segoe UI", "Arial"],
        "axes.unicode_minus": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })
    sns.set_theme(
        style="whitegrid",
        rc={
            "figure.facecolor": TOKENS["surface"],
            "axes.facecolor": TOKENS["panel"],
            "axes.edgecolor": TOKENS["axis"],
            "axes.labelcolor": TOKENS["ink"],
            "axes.spines.top": False,
            "axes.spines.right": False,
            "grid.color": TOKENS["grid"],
            "grid.linewidth": 0.8,
            "text.color": TOKENS["ink"],
            "xtick.color": TOKENS["muted"],
            "ytick.color": TOKENS["muted"],
            "legend.frameon": False,
            "patch.linewidth": 1.0,
        },
    )
    mpl.rcParams["font.family"] = "sans-serif"
    mpl.rcParams["font.sans-serif"] = ["DejaVu Sans", "Segoe UI", "Arial"]
    mpl.rcParams["axes.unicode_minus"] = False


def add_header(fig: plt.Figure, title: str, subtitle: str, *, left: float = 0.08) -> None:
    fig.text(left, 0.985, title, ha="left", va="top", fontsize=14, fontweight="semibold", color=TOKENS["ink"], fontproperties=CJK_FONT_PROP)
    fig.text(left, 0.94, subtitle, ha="left", va="top", fontsize=9, color=TOKENS["muted"], fontproperties=CJK_FONT_PROP)


def finish(fig: plt.Figure, stem: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_DIR / f"{stem}.png", dpi=240, bbox_inches="tight", facecolor=TOKENS["surface"])
    fig.savefig(OUT_DIR / f"{stem}.pdf", bbox_inches="tight", facecolor=TOKENS["surface"])
    plt.close(fig)


def coerce(value: str):
    if value in {"PASS", "FAIL", "ordered", "sorted"}:
        return value
    try:
        return float(value) if any(c in value for c in ".eE") else int(value)
    except ValueError:
        return value


def parse_stage(path: Path, accepted: set[str]) -> pd.DataFrame:
    rows = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = re.match(r"\[([^]]+)\]\s+(.*)", line)
        if not match or match.group(1) not in accepted:
            continue
        row = {"record_type": match.group(1)}
        row.update({key: coerce(value) for key, value in re.findall(r"(\w+)=([^\s]+)", match.group(2))})
        rows.append(row)
    return pd.DataFrame(rows)


def notebook_has_outputs(path: Path) -> bool:
    notebook = json.loads(path.read_text(encoding="utf-8"))
    outputs = [output for cell in notebook.get("cells", []) for output in cell.get("outputs", [])]
    return bool(outputs) and not any(output.get("output_type") == "error" for output in outputs)


def load_and_validate() -> dict[str, pd.DataFrame]:
    notebooks = [
        ROOT / "HIP_completed/HIP/Lab1_Vector_Addition/Lab1_vadd.ipynb",
        ROOT / "HIP_completed/HIP/Lab2_Matrix_Transpose/Lab2_Transpose.ipynb",
        ROOT / "HIP_completed/HIP/Lab3_Histogram/Lab3_Histogram.ipynb",
        ROOT / "HIP_completed/HIP/Lab4_Reduction/Lab4_Reduction.ipynb",
        ROOT / "HIP_completed/HIP/Lab5_Monte_Carlo_Integration/Lab5_MonteCarlo.ipynb",
        ROOT / "HIP_completed/HIP/Lab6_K-Means_Clustering/Lab6_KMeans.ipynb",
    ]
    for notebook in notebooks:
        if not notebook_has_outputs(notebook):
            raise RuntimeError(f"Notebook lacks clean execution outputs: {notebook}")

    stage1 = parse_stage(ROOT / "PCFG_GPU_stage1_completed/results/stage1_data_only.txt", {"bench"})
    stage2 = parse_stage(ROOT / "PCFG_GPU_stage2_completed/results/stage2_data_only.txt", {"bench", "multi-bench"})
    stage3 = parse_stage(ROOT / "PCFG_GPU_stage3_completed/results/stage3_data_only.txt", {"multi-bench", "overlap-bench"})
    stage4 = parse_stage(ROOT / "PCFG_GPU_stage4_completed/results/stage4_data_only.txt", {"schedule-bench"})
    expected_stage_rows = [(stage1, 15), (stage2, 30), (stage3, 30), (stage4, 5)]
    for frame, expected in expected_stage_rows:
        if len(frame) != expected or not (frame["correctness"] == "PASS").all():
            raise RuntimeError(f"Stage validation failed: expected {expected} PASS rows, found {len(frame)}")

    real = pd.read_csv(ROOT / "PCFG_GPU_real_completed/results/real_raw.csv")
    if len(real) != 90 or not (real["correctness"] == "PASS").all():
        raise RuntimeError("Real PCFG validation failed: expected 90 PASS rows")
    if not (real["count"] == real["limit"]).all():
        raise RuntimeError("Real PCFG candidate counts do not match requested limits")
    if not (real["hash"] == real["expected_hash"]).all():
        raise RuntimeError("Real PCFG FNV hashes do not match the CPU baseline")
    if not ((real["gpu_guesses"] + real["cpu_fallback_guesses"]) == real["count"]).all():
        raise RuntimeError("Real PCFG CPU/GPU routing is not conservative")
    group_sizes = real.groupby(["limit", "mode"]).size()
    if len(group_sizes) != 18 or not (group_sizes == 5).all():
        raise RuntimeError("Real PCFG does not contain five repeats for every scale and mode")

    pt_stats = pd.read_csv(ROOT / "PCFG_GPU_real_completed/results/real_pt_stats.csv")
    return {"stage1": stage1, "stage2": stage2, "stage3": stage3, "stage4": stage4, "real": real, "pt_stats": pt_stats}


def plot_vector_add() -> None:
    block = np.array([16, 32, 64, 128, 256, 512, 1024])
    mean = np.array([0.0355, 0.0237, 0.0242, 0.0210, 0.0236, 0.0244, 0.0286])
    std = np.array([0.0010, 0.0161, 0.0156, 0.0060, 0.0144, 0.0143, 0.0206])
    bandwidth = (3 * 4 * 1_048_576) / (mean / 1000) / 1e9
    fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.1))
    x = np.arange(len(block))
    axes[0].errorbar(x, mean, yerr=std, fmt="o-", color=COLORS["blue"]["mid"], ecolor=COLORS["blue"]["light"], capsize=3, lw=1.2)
    axes[0].set_xticks(x, block)
    axes[0].set_xlabel("Block size (threads)")
    axes[0].set_ylabel("Kernel time (ms)")
    axes[0].grid(axis="x", visible=False)
    axes[1].plot(x, bandwidth, "o-", color=COLORS["orange"]["mid"], lw=1.2)
    axes[1].set_xticks(x, block)
    axes[1].set_xlabel("Block size (threads)")
    axes[1].set_ylabel("Effective bandwidth (GB/s)")
    axes[1].grid(axis="x", visible=False)
    add_header(fig, "Vector Add 的 block size 与有效带宽", "N=1,048,576；每种配置 10 次；误差线为 1 个标准差")
    fig.tight_layout(rect=(0, 0, 1, 0.86))
    finish(fig, "basic_vector_add")


def plot_transpose() -> None:
    labels = ["16×16", "128×32", "1×1024", "1001×2001"]
    elements = np.array([256, 4096, 1024, 2_003_001])
    mean = np.array([0.0062, 0.0085, 0.0064, 0.1119])
    std = np.array([0.0026, 0.0020, 0.0021, 0.0019])
    per_element_ns = mean * 1e6 / elements
    fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.1))
    x = np.arange(len(labels))
    axes[0].bar(x, mean, yerr=std, capsize=3, color=COLORS["blue"]["base"], edgecolor=COLORS["blue"]["dark"])
    axes[0].set_xticks(x, labels)
    axes[0].set_yscale("log")
    axes[0].set_ylabel("Kernel time (ms, log)")
    axes[0].set_xlabel("Matrix dimensions")
    axes[0].grid(axis="x", visible=False)
    axes[1].bar(x, per_element_ns, color=COLORS["orange"]["base"], edgecolor=COLORS["orange"]["dark"])
    axes[1].set_xticks(x, labels)
    axes[1].set_yscale("log")
    axes[1].set_ylabel("Time per element (ns, log)")
    axes[1].set_xlabel("Matrix dimensions")
    axes[1].grid(axis="x", visible=False)
    add_header(fig, "Matrix Transpose 的规模效应", "HIP event kernel 时间；每组 10 次；直接转置采用连续读和跨步写")
    fig.tight_layout(rect=(0, 0, 1, 0.86))
    finish(fig, "basic_transpose")


def plot_histogram() -> None:
    cases = ["Medium\n10M / 64 bins", "Large\n100M / 512 bins"]
    times = {
        "Serial CPU": [2.3936, 23.3382],
        "Naive GPU": [5.5709, 360.7488],
        "Optimized GPU": [0.1866, 1.8208],
    }
    fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.2))
    x = np.arange(2)
    width = 0.24
    palette = [COLORS["blue"], COLORS["orange"], COLORS["olive"]]
    for idx, (name, values) in enumerate(times.items()):
        family = palette[idx]
        axes[0].bar(x + (idx - 1) * width, values, width, label=name, color=family["base"], edgecolor=family["dark"])
    axes[0].set_xticks(x, cases)
    axes[0].set_yscale("log")
    axes[0].set_ylabel("Compute time (ms, log)")
    axes[0].legend(loc="upper left", fontsize=8)
    axes[0].grid(axis="x", visible=False)
    speed_cpu = np.array(times["Serial CPU"]) / np.array(times["Optimized GPU"])
    speed_naive = np.array(times["Naive GPU"]) / np.array(times["Optimized GPU"])
    axes[1].bar(x - width / 2, speed_cpu, width, label="vs Serial CPU", color=COLORS["blue"]["base"], edgecolor=COLORS["blue"]["dark"])
    axes[1].bar(x + width / 2, speed_naive, width, label="vs Naive GPU", color=COLORS["orange"]["base"], edgecolor=COLORS["orange"]["dark"])
    axes[1].set_xticks(x, cases)
    axes[1].set_ylabel("Speedup (×)")
    axes[1].legend(loc="upper left", fontsize=8)
    axes[1].grid(axis="x", visible=False)
    add_header(fig, "Histogram 三种实现的计算阶段性能", "每组 5 次；不含文件输入输出；Optimized GPU 输出与 CPU 逐项一致")
    fig.tight_layout(rect=(0, 0, 1, 0.86))
    finish(fig, "basic_histogram")


def plot_reduction() -> None:
    strategy = ["Naive atomic", "Tree (LDS)", "Tree + shuffle", "Multi-element"]
    time_ms = np.array([0.0309, 0.0246, 0.0198, 0.0124])
    speedup = time_ms[0] / time_ms
    fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.0))
    y = np.arange(len(strategy))
    axes[0].barh(y, time_ms, color=COLORS["blue"]["base"], edgecolor=COLORS["blue"]["dark"])
    axes[0].set_yticks(y, strategy)
    axes[0].invert_yaxis()
    axes[0].set_xlabel("Kernel time (ms)")
    axes[0].grid(axis="y", visible=False)
    axes[1].plot(speedup, y, "o-", color=COLORS["orange"]["mid"], lw=1.2)
    axes[1].axvline(1.0, color=NEUTRAL["dark"], ls="--", lw=1)
    axes[1].set_yticks(y, strategy)
    axes[1].invert_yaxis()
    axes[1].set_xlabel("Speedup over Naive atomic (×)")
    axes[1].grid(axis="y", visible=False)
    add_header(fig, "Reduction 优化策略的递进效果", "N=1,000,000，block size=256；四种策略结果均为 -74,993,790")
    fig.tight_layout(rect=(0, 0, 1, 0.86))
    finish(fig, "basic_reduction")


def plot_scaling() -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.1))
    samples = np.array([100_000, 10_000_000, 100_000_000])
    wall = np.array([0.072, 0.894, 8.454])
    x = np.arange(3)
    axes[0].bar(x, wall, color=COLORS["blue"]["base"], edgecolor=COLORS["blue"]["dark"])
    axes[0].set_xticks(x, ["100K", "10M", "100M"])
    axes[0].set_yscale("log")
    axes[0].set_xlabel("Monte Carlo samples")
    axes[0].set_ylabel("Process wall time (s, log)")
    axes[0].grid(axis="x", visible=False)
    metrics = ["Data points", "Distance evals / iter.", "Global atomic upper bound"]
    counts = [50_000, 2_500_000, 29_400]
    y = np.arange(3)
    axes[1].barh(y, counts, color=COLORS["orange"]["base"], edgecolor=COLORS["orange"]["dark"])
    axes[1].set_yticks(y, metrics)
    axes[1].set_xscale("log")
    axes[1].set_xlabel("K-Means operation count (log)")
    axes[1].grid(axis="y", visible=False)
    axes[1].text(0.98, 0.05, "Measured wall time: 0.081 s\nN=50,000, k=50", transform=axes[1].transAxes, ha="right", va="bottom", fontsize=8, color=TOKENS["muted"])
    add_header(fig, "Monte Carlo 规模运行与 K-Means 实测工作负载", "墙钟时间包含进程与输入开销；K-Means 仅有一个带时间记录的规模，不推断趋势")
    fig.tight_layout(rect=(0, 0, 1, 0.86))
    finish(fig, "basic_scaling")


def plot_stage1(stage1: pd.DataFrame) -> None:
    means = stage1.groupby("batch")[["h2d_ms", "kernel_ms", "d2h_ms"]].mean().reindex([1024, 10000, 100000])
    fig, ax = plt.subplots(figsize=(8.2, 4.3))
    x = np.arange(len(means))
    bottom = np.zeros(len(means))
    fields = [("h2d_ms", "H2D", COLORS["blue"]), ("kernel_ms", "Kernel", COLORS["olive"]), ("d2h_ms", "D2H", COLORS["orange"])]
    for field, label, family in fields:
        values = means[field].to_numpy()
        ax.bar(x, values, bottom=bottom, label=label, color=family["base"], edgecolor=family["dark"])
        bottom += values
    ax.set_xticks(x, ["1,024", "10,000", "100,000"])
    ax.set_xlabel("Candidates per PT")
    ax.set_ylabel("Mean GPU component time (ms)")
    ax.legend(loc="upper left", ncol=3)
    ax.grid(axis="x", visible=False)
    add_header(fig, "Stage 1：单 PT 的传输与 kernel 时间分解", "每个规模 5 次；GPU total=H2D+kernel+D2H；不含 CPU 字符串生成")
    fig.tight_layout(rect=(0, 0, 1, 0.84))
    finish(fig, "pcfg_stage1_breakdown")


def plot_stage23(stage2: pd.DataFrame, stage3: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.1))
    single = stage2[stage2.record_type == "bench"].copy()
    single["pts"] = (single["batch"] / 10000).astype(int)
    multi = stage2[stage2.record_type == "multi-bench"]
    for frame, label, family, marker in [(single, "Single PT", COLORS["blue"], "o"), (multi, "Multi PT", COLORS["orange"], "s")]:
        stats = frame.groupby("pts")["gpu_total_ms"].agg(["mean", "std"]).reindex([2, 4, 8])
        axes[0].errorbar(stats.index, stats["mean"], yerr=stats["std"], marker=marker, color=family["mid"], ecolor=family["light"], capsize=3, label=label)
    axes[0].set_xticks([2, 4, 8])
    axes[0].set_xlabel("PT count (10K values each)")
    axes[0].set_ylabel("GPU total (ms)")
    axes[0].set_title("Same total candidate count")
    axes[0].legend(fontsize=8)
    for record_type, label, family, marker in [("multi-bench", "Sequential multi-PT", COLORS["blue"], "o"), ("overlap-bench", "Stream overlap", COLORS["orange"], "s")]:
        frame = stage3[stage3.record_type == record_type]
        stats = frame.groupby("pts")["gpu_total_ms"].agg(["mean", "std"]).reindex([2, 4, 8])
        axes[1].errorbar(stats.index, stats["mean"], yerr=stats["std"], marker=marker, color=family["mid"], ecolor=family["light"], capsize=3, label=label)
    axes[1].set_xticks([2, 4, 8])
    axes[1].set_xlabel("PT count (10K values each)")
    axes[1].set_ylabel("GPU total (ms)")
    axes[1].set_title("Packing overlap comparison")
    axes[1].legend(fontsize=8)
    add_header(fig, "Stage 2–3：多 PT 合并与 stream overlap", "每点 5 次；误差线为 1 个标准差；横轴为离散工作量配置")
    fig.tight_layout(rect=(0, 0, 1, 0.84))
    finish(fig, "pcfg_stage23_compare")


def plot_real_pt_distribution(pt_stats: pd.DataFrame) -> None:
    quantiles = ["min", "p50", "p90", "p99", "max"]
    fig, ax = plt.subplots(figsize=(8.8, 4.6))
    scale_colors = [COLORS["blue"], COLORS["olive"], COLORS["orange"]]
    for (_, row), family in zip(pt_stats.iterrows(), scale_colors):
        ax.plot(quantiles, [row[q] for q in quantiles], marker="o", lw=1.2, color=family["mid"], label=f"{int(row['limit']):,} candidates")
    ax.axhline(4096, color=COLORS["gold"]["dark"], ls="--", lw=1.1, label="Default min=4,096")
    ax.axhline(131072, color=NEUTRAL["dark"], ls=":", lw=1.1, label="Conservative min=131,072")
    ax.set_yscale("log")
    ax.set_xlabel("WorkUnit candidate-count quantile")
    ax.set_ylabel("Candidates per WorkUnit (log)")
    ax.legend(loc="upper left", ncol=2, fontsize=8)
    add_header(fig, "真实 PCFG 的 WorkUnit 大小分布与调度阈值", "共享任务集的 min、P50、P90、P99、max；1M 规模含 199 个 WorkUnit")
    fig.tight_layout(rect=(0, 0, 1, 0.84))
    finish(fig, "pcfg_real_pt_distribution")


def plot_real_performance(real: pd.DataFrame) -> None:
    mode_order = ["cpu", "single", "multi4", "overlap4", "schedule_default", "schedule_conservative"]
    labels = {
        "cpu": "CPU baseline",
        "single": "Single PT GPU",
        "multi4": "4-PT batch",
        "overlap4": "4-PT overlap",
        "schedule_default": "Default schedule",
        "schedule_conservative": "Conservative (CPU)",
    }
    families = {"cpu": NEUTRAL, "single": COLORS["blue"], "multi4": COLORS["olive"], "overlap4": COLORS["gold"], "schedule_default": COLORS["orange"], "schedule_conservative": COLORS["pink"]}
    limits = [10000, 100000, 1000000]
    fig, axes = plt.subplots(1, 2, figsize=(12.0, 4.6))
    x = np.arange(3)
    width = 0.12
    for idx, mode in enumerate(mode_order):
        stats = real[real["mode"] == mode].groupby("limit")["wall_ms"].agg(["mean", "std"]).reindex(limits)
        family = families[mode]
        axes[0].bar(x + (idx - 2.5) * width, stats["mean"], width, yerr=stats["std"], capsize=2, label=labels[mode], color=family["base"], edgecolor=family["dark"])
    axes[0].set_yscale("log")
    axes[0].set_xticks(x, ["10K", "100K", "1M"])
    axes[0].set_xlabel("Generated candidates")
    axes[0].set_ylabel("End-to-end wall time (ms, log)")
    axes[0].grid(axis="x", visible=False)
    axes[0].legend(loc="upper left", fontsize=7, ncol=2)

    non_cpu = mode_order[1:]
    offsets = np.linspace(-0.22, 0.22, len(non_cpu))
    for offset, mode in zip(offsets, non_cpu):
        family = families[mode]
        grouped = real[real["mode"] == mode].groupby("limit")["speedup"]
        med = grouped.median().reindex(limits)
        q1 = grouped.quantile(0.25).reindex(limits)
        q3 = grouped.quantile(0.75).reindex(limits)
        axes[1].errorbar(x + offset, med, yerr=[med - q1, q3 - med], fmt="o", color=family["mid"], ecolor=family["light"], capsize=3, label=labels[mode])
    axes[1].axhline(1.0, color=NEUTRAL["dark"], ls="--", lw=1.1)
    axes[1].set_yscale("log")
    axes[1].set_xticks(x, ["10K", "100K", "1M"])
    axes[1].set_xlabel("Generated candidates")
    axes[1].set_ylabel("Paired CPU speedup, median (log)")
    axes[1].legend(loc="upper left", fontsize=7, ncol=2)
    add_header(fig, "真实 PCFG 的端到端时间与同轮 CPU speedup", "每种规模与模式各 5 次；左图为 mean±SD，右图为 median 和四分位区间")
    fig.tight_layout(rect=(0, 0, 1, 0.84))
    finish(fig, "pcfg_real_performance")


def plot_real_routing(real: pd.DataFrame) -> None:
    labels = {
        "cpu": "CPU baseline", "single": "Single PT GPU", "multi4": "4-PT batch",
        "overlap4": "4-PT overlap", "schedule_default": "Default schedule",
        "schedule_conservative": "Conservative schedule",
    }
    mode_order = ["cpu", "single", "multi4", "overlap4", "schedule_default", "schedule_conservative"]
    frame = real[(real["limit"] == 1_000_000) & (real["repeat"] == 1)].set_index("mode").loc[mode_order]
    cpu_share = frame["cpu_fallback_guesses"].to_numpy() / frame["count"].to_numpy() * 100
    gpu_share = frame["gpu_guesses"].to_numpy() / frame["count"].to_numpy() * 100
    fig, ax = plt.subplots(figsize=(8.8, 4.6))
    y = np.arange(len(mode_order))
    ax.barh(y, cpu_share, label="CPU", color=COLORS["orange"]["base"], edgecolor=COLORS["orange"]["dark"])
    ax.barh(y, gpu_share, left=cpu_share, label="GPU", color=COLORS["blue"]["base"], edgecolor=COLORS["blue"]["dark"])
    ax.set_yticks(y, [labels[m] for m in mode_order])
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.xaxis.set_major_formatter(mticker.PercentFormatter(100))
    ax.set_xlabel("Candidate routing share")
    ax.legend(loc="upper left", ncol=2)
    ax.grid(axis="y", visible=False)
    add_header(fig, "1M 真实候选的 CPU/GPU 分流", "Default schedule: 940,796 GPU + 59,204 CPU；Conservative schedule 全部进入 CPU 路径")
    fig.tight_layout(rect=(0, 0, 1, 0.84))
    finish(fig, "pcfg_real_routing")


def plot_cold_start(real: pd.DataFrame) -> None:
    cpu = real[(real["limit"] == 1_000_000) & (real["mode"] == "cpu")].sort_values("repeat")
    warm_mean = cpu[cpu["repeat"] > 1]["wall_ms"].mean()
    fig, ax = plt.subplots(figsize=(8.2, 4.4))
    colors = [COLORS["orange"]["base"]] + [COLORS["blue"]["base"]] * 4
    edges = [COLORS["orange"]["dark"]] + [COLORS["blue"]["dark"]] * 4
    bars = ax.bar(cpu["repeat"], cpu["wall_ms"], color=colors, edgecolor=edges)
    ax.axhline(warm_mean, color=NEUTRAL["dark"], ls="--", lw=1.1, label=f"Repeats 2–5 mean = {warm_mean:.2f} ms")
    for bar, value in zip(bars, cpu["wall_ms"]):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 10, f"{value:.1f}", ha="center", va="bottom", fontsize=8)
    ax.set_xticks(cpu["repeat"])
    ax.set_xlabel("Repeat")
    ax.set_ylabel("CPU GenerateRange wall time (ms)")
    ax.set_ylim(0, cpu["wall_ms"].max() * 1.14)
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(axis="x", visible=False)
    add_header(fig, "1M CPU baseline 的首轮冷启动与稳态区间", "Repeat 1=688.84 ms；repeats 2–5 mean=219.74 ms、SD=9.65 ms")
    fig.tight_layout(rect=(0, 0, 1, 0.84))
    finish(fig, "pcfg_real_cold_start")


def main() -> None:
    use_chart_theme()
    data = load_and_validate()
    plot_vector_add()
    plot_transpose()
    plot_histogram()
    plot_reduction()
    plot_scaling()
    plot_stage1(data["stage1"])
    plot_stage23(data["stage2"], data["stage3"])
    plot_real_pt_distribution(data["pt_stats"])
    plot_real_performance(data["real"])
    plot_real_routing(data["real"])
    plot_cold_start(data["real"])
    print("Validation PASS: 6 notebooks, 80 staged benchmark rows, 90 real benchmark rows")
    print(f"Generated 11 figures in {OUT_DIR}")


if __name__ == "__main__":
    main()
