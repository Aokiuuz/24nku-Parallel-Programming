#!/usr/bin/env python3
"""Create report-ready real-PCFG charts from validated CSV files."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


PALETTE = {
    "cpu": "#3B4CC0",
    "single": "#1F9E89",
    "multi4": "#35B779",
    "overlap4": "#90D743",
    "schedule_default": "#F89540",
    "schedule_conservative": "#D1495B",
}
LABELS = {
    "cpu": "CPU baseline",
    "single": "Single PT GPU",
    "multi4": "4-PT batch",
    "overlap4": "4-PT overlap",
    "schedule_default": "Default schedule",
    "schedule_conservative": "Conservative schedule",
}
MODE_ORDER = list(PALETTE)


def configure_style() -> None:
    sns.set_theme(
        context="paper",
        style="whitegrid",
        font_scale=1.05,
        rc={
            "figure.facecolor": "#FCFCFA",
            "axes.facecolor": "#FCFCFA",
            "axes.edgecolor": "#333333",
            "grid.color": "#D9D9D9",
            "grid.linewidth": 0.6,
            "axes.titleweight": "bold",
            "axes.labelcolor": "#222222",
            "text.color": "#222222",
            "legend.frameon": False,
        },
    )


def title_with_subtitle(ax: plt.Axes, title: str, subtitle: str) -> None:
    ax.set_title(title, loc="left", fontsize=13, pad=22)
    ax.text(0, 1.015, subtitle, transform=ax.transAxes, fontsize=9, color="#555555", va="bottom")


def save_figure(fig: plt.Figure, out_dir: Path, stem: str) -> None:
    fig.savefig(out_dir / f"{stem}.png", dpi=220, bbox_inches="tight", facecolor=fig.get_facecolor())
    fig.savefig(out_dir / f"{stem}.svg", bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def plot_pt_profile(stats: pd.DataFrame, out_dir: Path) -> None:
    quantiles = ["min", "p50", "p90", "p99", "max"]
    long = stats.melt(id_vars=["limit"], value_vars=quantiles, var_name="quantile", value_name="guesses")
    long["scale"] = long["limit"].map(lambda value: f"{int(value):,}")
    fig, ax = plt.subplots(figsize=(9.0, 4.2), constrained_layout=True)
    sns.lineplot(
        data=long,
        x="quantile",
        y="guesses",
        hue="scale",
        marker="o",
        linewidth=2,
        palette=["#3B4CC0", "#1F9E89", "#D1495B"],
        ax=ax,
    )
    ax.axhline(4096, color="#F89540", linestyle="--", linewidth=1.3, label="Default min = 4,096")
    ax.axhline(131072, color="#7A5195", linestyle=":", linewidth=1.5, label="Conservative min = 131,072")
    ax.set_yscale("log")
    ax.set_xlabel("WorkUnit candidate-count quantile")
    ax.set_ylabel("Candidates per real PT / WorkUnit")
    title_with_subtitle(
        ax,
        "Real PCFG task-size profile and scheduling thresholds",
        "Exact min, P50, P90, P99 and max from the shared task set at each generation scale",
    )
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(
        handles,
        labels,
        title="Scale / threshold",
        ncol=1,
        loc="upper left",
        bbox_to_anchor=(1.01, 1.0),
    )
    save_figure(fig, out_dir, "real_pt_distribution_thresholds")


def plot_wall_time(raw: pd.DataFrame, out_dir: Path) -> None:
    data = raw.copy()
    data["scale"] = data["limit"].map(lambda value: f"{int(value):,}")
    data["mode_label"] = data["mode"].map(LABELS)
    order = [LABELS[mode] for mode in MODE_ORDER]
    palette = {LABELS[mode]: PALETTE[mode] for mode in MODE_ORDER}
    fig, ax = plt.subplots(figsize=(8.4, 4.6), constrained_layout=True)
    sns.barplot(
        data=data,
        x="scale",
        y="wall_ms",
        hue="mode_label",
        hue_order=order,
        palette=palette,
        errorbar="sd",
        capsize=0.08,
        ax=ax,
    )
    ax.set_yscale("log")
    ax.set_xlabel("Generated candidates")
    ax.set_ylabel("End-to-end wall time (ms, log scale)")
    title_with_subtitle(
        ax,
        "Real PCFG end-to-end generation time",
        "Bars show five-run means; error bars show one standard deviation",
    )
    ax.legend(title=None, ncol=2, loc="upper left")
    save_figure(fig, out_dir, "real_mode_wall_time")


def plot_speedup(raw: pd.DataFrame, out_dir: Path) -> None:
    data = raw[raw["mode"] != "cpu"].copy()
    data["scale"] = data["limit"].map(lambda value: f"{int(value):,}")
    data["mode_label"] = data["mode"].map(LABELS)
    order = [LABELS[mode] for mode in MODE_ORDER if mode != "cpu"]
    palette = {LABELS[mode]: PALETTE[mode] for mode in MODE_ORDER if mode != "cpu"}
    fig, ax = plt.subplots(figsize=(9.0, 4.4), constrained_layout=True)
    sns.pointplot(
        data=data,
        x="scale",
        y="speedup",
        hue="mode_label",
        hue_order=order,
        palette=palette,
        errorbar="sd",
        markers="o",
        linestyles="-",
        dodge=0.18,
        ax=ax,
    )
    ax.axhline(1.0, color="#222222", linestyle="--", linewidth=1.2)
    ax.set_yscale("log")
    ax.set_xlabel("Generated candidates")
    ax.set_ylabel("Speedup over same-repeat CPU baseline (log scale)")
    title_with_subtitle(
        ax,
        "Real PCFG speedup by execution mode",
        "The dashed line marks parity with CPU; values below one represent a measured slowdown",
    )
    ax.legend(title=None, ncol=1, loc="upper left", bbox_to_anchor=(1.01, 1.0))
    save_figure(fig, out_dir, "real_mode_speedup")


def plot_single_breakdown(raw: pd.DataFrame, out_dir: Path) -> None:
    components = ["host_pack_ms", "h2d_ms", "kernel_ms", "d2h_ms", "host_unpack_ms"]
    labels = ["Host pack", "H2D", "Kernel", "D2H", "Host unpack"]
    colors = ["#7A5195", "#EF5675", "#35B779", "#FFA600", "#4C78A8"]
    data = raw[raw["mode"] == "single"].groupby("limit", as_index=False)[components].mean()
    long = data.melt(id_vars="limit", value_vars=components, var_name="component", value_name="time_ms")
    long["component"] = long["component"].map(dict(zip(components, labels)))
    long["scale"] = long["limit"].map(lambda value: f"{int(value):,}")
    fig, ax = plt.subplots(figsize=(7.8, 4.3), constrained_layout=True)
    sns.lineplot(
        data=long,
        x="scale",
        y="time_ms",
        hue="component",
        hue_order=labels,
        palette=dict(zip(labels, colors)),
        marker="o",
        linewidth=2,
        ax=ax,
    )
    ax.set_yscale("log")
    ax.set_xlabel("Generated candidates")
    ax.set_ylabel("Mean measured component time (ms, log scale)")
    title_with_subtitle(
        ax,
        "Single-PT GPU data-path time composition",
        "Host conversion is reported separately; lines cover packing, transfer, kernel and restoration",
    )
    ax.legend(title=None, ncol=3, loc="upper left")
    save_figure(fig, out_dir, "real_single_timing_breakdown")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", type=Path, default=Path("results"))
    args = parser.parse_args()
    out_dir = args.results_dir / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    configure_style()
    raw = pd.read_csv(args.results_dir / "real_raw.csv")
    stats = pd.read_csv(args.results_dir / "real_pt_stats.csv")
    plot_pt_profile(stats, out_dir)
    plot_wall_time(raw, out_dir)
    plot_speedup(raw, out_dir)
    plot_single_breakdown(raw, out_dir)
    print(f"Created real-PCFG figures in {out_dir}")


if __name__ == "__main__":
    main()
