import asyncio
import csv
import json
import socket
import statistics
import threading
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import matplotlib.pyplot as plt
import pandas as pd
import psutil


HOST = "127.0.0.1"
SERVER_DELAY_SECONDS = 0.02
IO_TASK_COUNTS = [100, 500, 1000, 3000, 5000]
ASYNC_CONNECTION_LIMIT = 50
THREAD_WORKERS = [50, 100, 200]
CPU_TASK_COUNTS = [50, 100, 200]
CPU_ITERATIONS = 5000
REPEATS = 5
SAMPLE_INTERVAL_SECONDS = 0.005


@dataclass
class TcpServerHandle:
    port: int
    stop: Callable[[], None]
    thread: threading.Thread


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        while True:
            request = await reader.readline()
            if not request:
                break
            await asyncio.sleep(SERVER_DELAY_SECONDS)
            writer.write(b"OK\n")
            await writer.drain()
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except ConnectionError:
            pass


def start_tcp_server() -> TcpServerHandle:
    ready = threading.Event()
    state: dict[str, object] = {}

    def server_thread() -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        stop_future = loop.create_future()
        state["loop"] = loop
        state["stop_future"] = stop_future

        async def runner() -> None:
            server = await asyncio.start_server(
                handle_client,
                HOST,
                0,
                backlog=4096,
                reuse_address=True,
            )
            state["server"] = server
            state["port"] = server.sockets[0].getsockname()[1]
            ready.set()
            await stop_future
            server.close()
            await server.wait_closed()
            await asyncio.sleep(0.05)

        try:
            loop.run_until_complete(runner())
        finally:
            pending = [task for task in asyncio.all_tasks(loop) if not task.done()]
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            loop.close()

    thread = threading.Thread(target=server_thread, name="local-tcp-io-server", daemon=True)
    thread.start()
    if not ready.wait(timeout=10):
        raise RuntimeError("Local TCP server did not start within 10 seconds.")

    def stop() -> None:
        loop = state.get("loop")
        stop_future = state.get("stop_future")
        if loop and stop_future and not stop_future.done():
            loop.call_soon_threadsafe(stop_future.set_result, None)
        thread.join(timeout=10)
        if thread.is_alive():
            raise RuntimeError("Local TCP server did not stop cleanly.")

    return TcpServerHandle(port=int(state["port"]), stop=stop, thread=thread)


def distribute(total: int, buckets: int) -> list[int]:
    buckets = max(1, min(total, buckets))
    base, remainder = divmod(total, buckets)
    return [base + (1 if index < remainder else 0) for index in range(buckets)]


async def async_tcp_worker(port: int, request_count: int) -> int:
    reader, writer = await asyncio.open_connection(HOST, port)
    completed = 0
    try:
        for _ in range(request_count):
            writer.write(b"PING\n")
            await writer.drain()
            response = await reader.readline()
            completed += 1 if response == b"OK\n" else 0
    finally:
        writer.close()
        await writer.wait_closed()
    return completed


async def run_async_tcp_once(task_count: int, port: int) -> int:
    partitions = distribute(task_count, ASYNC_CONNECTION_LIMIT)
    tasks = [async_tcp_worker(port, count) for count in partitions]
    return sum(await asyncio.gather(*tasks))


def blocking_tcp_worker(port: int, request_count: int) -> int:
    completed = 0
    with socket.create_connection((HOST, port), timeout=10) as sock:
        for _ in range(request_count):
            sock.sendall(b"PING\n")
            data = b""
            while not data.endswith(b"\n"):
                chunk = sock.recv(16)
                if not chunk:
                    break
                data += chunk
            completed += 1 if data == b"OK\n" else 0
    return completed


def run_thread_tcp_once(task_count: int, workers: int, port: int) -> int:
    partitions = distribute(task_count, workers)
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix=f"io-{workers}") as executor:
        return sum(executor.map(lambda count: blocking_tcp_worker(port, count), partitions))


def cpu_work(iterations: int = CPU_ITERATIONS) -> int:
    value = 0
    for i in range(iterations):
        value = (value * 1664525 + i + 1013904223) & 0xFFFFFFFF
    return value


async def async_cpu_task() -> int:
    return cpu_work()


async def run_async_cpu_once(task_count: int) -> int:
    results = await asyncio.gather(*(async_cpu_task() for _ in range(task_count)))
    return len(results)


def run_thread_cpu_once(task_count: int, workers: int) -> int:
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix=f"cpu-{workers}") as executor:
        return sum(1 for _ in executor.map(lambda _: cpu_work(), range(task_count)))


def measure_repeats(
    *,
    scenario: str,
    task_count: int,
    model: str,
    workers: int | str,
    label: str,
    fn: Callable[[], int],
    baseline_threads: int,
    process: psutil.Process,
) -> list[dict[str, object]]:
    rows = []
    for repeat in range(1, REPEATS + 1):
        stop_sampling = threading.Event()
        peak_threads = [threading.active_count()]
        rss_before = process.memory_info().rss
        peak_rss = [rss_before]

        def sample() -> None:
            while not stop_sampling.is_set():
                peak_threads[0] = max(peak_threads[0], threading.active_count())
                peak_rss[0] = max(peak_rss[0], process.memory_info().rss)
                time.sleep(SAMPLE_INTERVAL_SECONDS)

        sampler = threading.Thread(target=sample, name="metric-sampler")
        tracemalloc.start()
        sampler.start()
        start = time.perf_counter()
        try:
            completed = fn()
            duration = time.perf_counter() - start
            _, trace_peak = tracemalloc.get_traced_memory()
        finally:
            stop_sampling.set()
            sampler.join()
            tracemalloc.stop()

        extra_threads = max(0, peak_threads[0] - baseline_threads - 1)
        rows.append(
            {
                "scenario": scenario,
                "task_count": task_count,
                "model": model,
                "workers": workers,
                "label": label,
                "repeat": repeat,
                "duration_seconds": duration,
                "throughput_tasks_per_second": completed / duration,
                "peak_extra_python_threads": extra_threads,
                "peak_rss_delta_mb": max(0, peak_rss[0] - rss_before) / (1024 * 1024),
                "peak_tracemalloc_mb": trace_peak / (1024 * 1024),
                "completed_tasks": completed,
            }
        )
    return rows


def summarize(detail_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    data = pd.DataFrame(detail_rows)
    group_cols = ["scenario", "task_count", "model", "workers", "label"]
    metrics = [
        "duration_seconds",
        "throughput_tasks_per_second",
        "peak_extra_python_threads",
        "peak_rss_delta_mb",
        "peak_tracemalloc_mb",
        "completed_tasks",
    ]
    rows = []
    for keys, subset in data.groupby(group_cols, dropna=False):
        row = {key: to_builtin(value) for key, value in zip(group_cols, keys)}
        row["repeats"] = int(subset["repeat"].count())
        for metric in metrics:
            values = subset[metric]
            row[f"{metric}_median"] = float(values.median())
            row[f"{metric}_mean"] = float(values.mean())
            row[f"{metric}_min"] = float(values.min())
            row[f"{metric}_max"] = float(values.max())
        rows.append(row)
    return rows


def to_builtin(value):
    if pd.isna(value):
        return ""
    if hasattr(value, "item"):
        return value.item()
    return value


def frame_records(path: Path) -> list[dict[str, object]]:
    data = pd.read_csv(path)
    return [{key: to_builtin(value) for key, value in row.items()} for row in data.to_dict("records")]


def series_name(row: pd.Series) -> str:
    return row["model"] if pd.isna(row["workers"]) or row["workers"] == "" else f"{row['model']}-{int(row['workers'])}"


def save_chart(fig: plt.Figure, out_dir: Path, stem: str) -> None:
    for ext in ("png", "svg"):
        fig.savefig(out_dir / f"{stem}.{ext}", dpi=220, bbox_inches="tight")
    plt.close(fig)


def style_axes(ax, title: str, ylabel: str) -> None:
    ax.set_title(title, loc="left", fontsize=16, fontweight="bold", pad=16)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.25)


def annotate_bars(ax, fmt="{:.2f}") -> None:
    for container in ax.containers:
        labels = []
        for value in container.datavalues:
            if value >= 100:
                labels.append(f"{value:.0f}")
            elif value >= 10:
                labels.append(f"{value:.1f}")
            else:
                labels.append(fmt.format(value))
        ax.bar_label(container, labels=labels, padding=3, fontsize=9)


def render_charts(summary_path: Path, out_dir: Path) -> None:
    out_dir.mkdir(exist_ok=True)
    data = pd.read_csv(summary_path)
    data["series"] = data.apply(series_name, axis=1)
    io = data[data["scenario"] == "tcp_io"].copy()
    cpu = data[data["scenario"] == "cpu_bound"].copy()
    max_io_count = int(io["task_count"].max())

    main_io = io[io["task_count"] == max_io_count].copy()
    order = ["asyncio", "threads-50", "threads-100", "threads-200"]
    main_io["series"] = pd.Categorical(main_io["series"], categories=order, ordered=True)
    main_io = main_io.sort_values("series")

    fig, ax = plt.subplots(figsize=(9.5, 5.3))
    ax.bar(main_io["series"].astype(str), main_io["duration_seconds_median"], color=["#2563EB", "#CBD5E1", "#94A3B8", "#64748B"])
    style_axes(ax, f"{max_io_count} TCP requests: asyncio finishes with less waiting overhead", "Median duration (s)")
    annotate_bars(ax)
    ax.set_xlabel("")
    save_chart(fig, out_dir, "exp_io_duration_bar")

    fig, ax = plt.subplots(figsize=(9.5, 5.3))
    ax.bar(main_io["series"].astype(str), main_io["peak_extra_python_threads_median"], color=["#2563EB", "#CBD5E1", "#94A3B8", "#64748B"])
    style_axes(ax, f"{max_io_count} TCP requests: thread pool buys speed with threads", "Peak extra Python threads")
    annotate_bars(ax, "{:.0f}")
    ax.set_xlabel("")
    save_chart(fig, out_dir, "exp_io_thread_bar")

    scaling = io[io["series"].isin(["asyncio", "threads-200"])].pivot(
        index="task_count",
        columns="series",
        values="duration_seconds_median",
    )
    fig, ax = plt.subplots(figsize=(9.5, 5.3))
    ax.plot(scaling.index, scaling["asyncio"], marker="o", linewidth=3.2, color="#2563EB", label="asyncio")
    ax.plot(scaling.index, scaling["threads-200"], marker="o", linewidth=3.2, color="#64748B", label="threads-200")
    style_axes(ax, "Scaling: compare the best thread pool against asyncio", "Median duration (s)")
    ax.set_xlabel("TCP request count")
    ax.legend(frameon=False)
    save_chart(fig, out_dir, "exp_io_scaling_async_vs_thread200")

    ratio = scaling["threads-200"] / scaling["asyncio"]
    fig, ax = plt.subplots(figsize=(9.5, 5.3))
    ax.bar([str(x) for x in ratio.index], ratio.values, color="#7C3AED")
    style_axes(ax, "Duration ratio: threads-200 / asyncio", "Ratio")
    annotate_bars(ax, "{:.2f}x")
    ax.axhline(1.0, color="#111827", linewidth=1.4, alpha=0.7)
    ax.set_xlabel("TCP request count")
    save_chart(fig, out_dir, "exp_io_ratio")

    max_cpu_count = int(cpu["task_count"].max())
    cpu_main = cpu[cpu["task_count"] == max_cpu_count].copy()
    cpu_main["series"] = pd.Categorical(cpu_main["series"], categories=order, ordered=True)
    cpu_main = cpu_main.sort_values("series")
    baseline = float(cpu_main[cpu_main["series"].astype(str) == "asyncio"]["duration_seconds_median"].iloc[0])
    cpu_main["normalized_duration"] = cpu_main["duration_seconds_median"] / baseline
    fig, ax = plt.subplots(figsize=(9.5, 5.3))
    ax.bar(cpu_main["series"].astype(str), cpu_main["normalized_duration"], color=["#2563EB", "#CBD5E1", "#94A3B8", "#64748B"])
    style_axes(ax, f"{max_cpu_count} CPU tasks: coroutine does not create CPU parallelism", "Normalized duration (asyncio = 1.0)")
    annotate_bars(ax, "{:.2f}x")
    ax.axhline(1.0, color="#111827", linewidth=1.4, alpha=0.7)
    ax.set_xlabel("")
    save_chart(fig, out_dir, "exp_cpu_normalized_duration")


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    out_dir = Path(__file__).resolve().parent
    asset_dir = out_dir / "assets"
    asset_dir.mkdir(exist_ok=True)
    process = psutil.Process()

    detail_rows: list[dict[str, object]] = []
    server = start_tcp_server()
    try:
        baseline_threads = threading.active_count()
        for count in IO_TASK_COUNTS:
            detail_rows.extend(
                measure_repeats(
                    scenario="tcp_io",
                    task_count=count,
                    model="asyncio",
                    workers="",
                    label="asyncio-tcp",
                    fn=lambda count=count: asyncio.run(run_async_tcp_once(count, server.port)),
                    baseline_threads=baseline_threads,
                    process=process,
                )
            )
            for workers in THREAD_WORKERS:
                detail_rows.extend(
                    measure_repeats(
                        scenario="tcp_io",
                        task_count=count,
                        model="threads",
                        workers=workers,
                        label=f"threads-tcp-{workers}",
                        fn=lambda count=count, workers=workers: run_thread_tcp_once(count, workers, server.port),
                        baseline_threads=baseline_threads,
                        process=process,
                    )
                )
    finally:
        server.stop()

    baseline_threads = threading.active_count()
    for count in CPU_TASK_COUNTS:
        detail_rows.extend(
            measure_repeats(
                scenario="cpu_bound",
                task_count=count,
                model="asyncio",
                workers="",
                label="asyncio-cpu",
                fn=lambda count=count: asyncio.run(run_async_cpu_once(count)),
                baseline_threads=baseline_threads,
                process=process,
            )
        )
        for workers in THREAD_WORKERS:
            detail_rows.extend(
                measure_repeats(
                    scenario="cpu_bound",
                    task_count=count,
                    model="threads",
                    workers=workers,
                    label=f"threads-cpu-{workers}",
                    fn=lambda count=count, workers=workers: run_thread_cpu_once(count, workers),
                    baseline_threads=baseline_threads,
                    process=process,
                )
            )

    summary_rows = summarize(detail_rows)
    detail_path = out_dir / "协程技术调研-实验明细.csv"
    summary_path = out_dir / "协程技术调研-实验汇总.csv"
    json_path = out_dir / "协程技术调研-实验数据.json"
    write_csv(detail_path, detail_rows)
    write_csv(summary_path, summary_rows)
    json_path.write_text(
        json.dumps({"detail": detail_rows, "summary": summary_rows}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    render_charts(summary_path, asset_dir)

    print(
        json.dumps(
            {
                "detail": str(detail_path),
                "summary": str(summary_path),
                "json": str(json_path),
                "detail_rows": len(detail_rows),
                "summary_rows": len(summary_rows),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
