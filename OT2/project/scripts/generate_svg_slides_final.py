import re
from html import escape
from pathlib import Path

import pandas as pd
from matplotlib.font_manager import FontProperties
from matplotlib.path import Path as MplPath
from matplotlib.textpath import TextPath


SCRIPT_DIR = Path(__file__).resolve().parent


def find_project_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "final").exists() or (candidate / "协程技术调研-实验汇总.csv").exists():
            return candidate
    return start


ROOT = find_project_root(SCRIPT_DIR)
DATA_DIR = ROOT / "project" / "experiment" if (ROOT / "project" / "experiment").exists() else ROOT
ASSETS = ROOT / "project" / "assets" if (ROOT / "project" / "assets").exists() else ROOT / "assets"
OUT = ROOT / "final" / "svg_slides"
OUT.mkdir(parents=True, exist_ok=True)
TOTAL_SLIDES = 20
STUDENT_INFO = "2412727  ， 刘蔚霖"
TEXT_OUTLINE_FONT = next(
    candidate
    for candidate in [
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simsun.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
    ]
    if candidate.exists()
)


def _svg_number(value):
    return f"{value:.3f}".rstrip("0").rstrip(".")


def text_outline_path(value, x, baseline_y, size, fill, weight=None):
    prop = FontProperties(fname=str(TEXT_OUTLINE_FONT))
    text_path = TextPath((0, 0), value, size=size, prop=prop)
    bbox = text_path.get_extents()
    translate_x = x - (bbox.x0 + bbox.x1) / 2
    commands = []
    for verts, code in text_path.iter_segments():
        nums = [_svg_number(v) for v in verts]
        if code == MplPath.MOVETO:
            commands.append(f"M {nums[0]} {nums[1]}")
        elif code == MplPath.LINETO:
            commands.append(f"L {nums[0]} {nums[1]}")
        elif code == MplPath.CURVE3:
            commands.append(f"Q {nums[0]} {nums[1]} {nums[2]} {nums[3]}")
        elif code == MplPath.CURVE4:
            commands.append(f"C {nums[0]} {nums[1]} {nums[2]} {nums[3]} {nums[4]} {nums[5]}")
        elif code == MplPath.CLOSEPOLY:
            commands.append("Z")
    return (
        f'<path d="{" ".join(commands)}" fill="{fill}" '
        f'transform="translate({_svg_number(translate_x)} {_svg_number(baseline_y)}) scale(1 -1)"/>'
    )


def text(x, y, value, cls="body", anchor="start"):
    return f'<text x="{x}" y="{y}" class="{cls}" text-anchor="{anchor}">{escape(str(value))}</text>'


def card(x, y, w, h, cls="card", accent="#2563EB"):
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="22" class="{cls}"/>'
        f'<rect x="{x}" y="{y}" width="6" height="{h}" rx="3" fill="{accent}" opacity="0.95"/>'
    )


def bullets(x, y, items, gap=30, cls="body", color="#60A5FA"):
    parts = []
    for index, item in enumerate(items):
        yy = y + gap * index
        parts.append(f'<circle cx="{x}" cy="{yy - 5}" r="4.5" fill="{color}"/>')
        parts.append(text(x + 18, yy, item, cls))
    return "\n".join(parts)


def pill(x, y, w, value, fill):
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="30" rx="15" fill="{fill}" opacity="0.96"/>'
        f'<text x="{x + w / 2}" y="{y + 20}" text-anchor="middle" fill="#FFFFFF" font-size="14" '
        f'font-weight="850">{escape(value)}</text>'
    )


def page(slide_no, kicker, title, subtitle, body):
    sub = text(50, 128, subtitle, "body") if subtitle else ""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720" role="img" aria-label="{escape(title)}">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#0B1020"/>
      <stop offset="55%" stop-color="#111827"/>
      <stop offset="100%" stop-color="#172033"/>
    </linearGradient>
    <linearGradient id="blue" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#60A5FA"/>
      <stop offset="100%" stop-color="#2563EB"/>
    </linearGradient>
    <style>
      .page {{ font-family: "Microsoft YaHei", "Microsoft YaHei UI", "DengXian", "SimSun", "NSimSun", "Segoe UI", Arial, sans-serif; }}
      .card {{ fill: rgba(255,255,255,0.078); stroke: rgba(255,255,255,0.15); stroke-width: 1.1; }}
      .card2 {{ fill: rgba(255,255,255,0.112); stroke: rgba(255,255,255,0.20); stroke-width: 1.1; }}
      .chartcard {{ fill: rgba(248,250,252,0.97); stroke: rgba(255,255,255,0.12); stroke-width: 1.1; }}
      .kicker {{ fill: #93C5FD; font-size: 14.5px; font-weight: 850; letter-spacing: 1.7px; }}
      .title {{ fill: #F8FAFC; font-size: 39px; font-weight: 850; letter-spacing: 0; }}
      .h1 {{ fill: #F8FAFC; font-size: 52px; font-weight: 850; letter-spacing: 0; }}
      .h2 {{ fill: #F8FAFC; font-size: 24px; font-weight: 820; letter-spacing: 0; }}
      .h3 {{ fill: #E5E7EB; font-size: 19.5px; font-weight: 780; letter-spacing: 0; }}
      .body {{ fill: #CBD5E1; font-size: 16.8px; font-weight: 540; letter-spacing: 0; }}
      .body2 {{ fill: #E2E8F0; font-size: 19.2px; font-weight: 620; letter-spacing: 0; }}
      .small {{ fill: #94A3B8; font-size: 13.5px; font-weight: 520; letter-spacing: 0; }}
      .metric {{ fill: #F8FAFC; font-size: 44px; font-weight: 850; letter-spacing: 0; }}
      .axis {{ stroke: rgba(255,255,255,0.22); stroke-width: 1; }}
      .node {{ fill: rgba(15,23,42,0.75); stroke: rgba(255,255,255,0.18); stroke-width: 1.1; }}
      .line {{ fill: none; stroke-width: 4; stroke-linecap: round; stroke-linejoin: round; }}
    </style>
  </defs>
  <rect class="page" width="1280" height="720" fill="url(#bg)"/>
  <circle cx="1126" cy="-88" r="282" fill="#2563EB" opacity="0.12"/>
  <circle cx="-86" cy="650" r="310" fill="#059669" opacity="0.10"/>
  <g class="page">
    {text(50, 52, kicker, "kicker")}
    {text(50, 96, title, "title")}
    {sub}
{body}
  </g>
  <text x="1232" y="692" text-anchor="end" class="small">{slide_no:02d}/{TOTAL_SLIDES:02d}</text>
</svg>
'''


def centered_title_page(slide_no):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720" role="img" aria-label="协程技术调研">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#0B1020"/>
      <stop offset="55%" stop-color="#111827"/>
      <stop offset="100%" stop-color="#172033"/>
    </linearGradient>
    <style>
      .page {{ font-family: "Microsoft YaHei", "Microsoft YaHei UI", "DengXian", "SimSun", "NSimSun", "Segoe UI", Arial, sans-serif; }}
      .small {{ fill: #94A3B8; font-size: 12.5px; font-weight: 520; letter-spacing: 0; }}
    </style>
  </defs>
  <rect class="page" width="1280" height="720" fill="url(#bg)"/>
  <circle cx="1126" cy="-88" r="282" fill="#2563EB" opacity="0.12"/>
  <circle cx="-86" cy="650" r="310" fill="#059669" opacity="0.10"/>
  <g class="page">
    <text x="640" y="328" text-anchor="middle" fill="#F8FAFC" font-size="58" font-weight="850">协程技术调研</text>
    {text_outline_path(STUDENT_INFO, 640, 392, 24, "#CBD5E1")}
  </g>
  <text x="1232" y="692" text-anchor="end" class="small">{slide_no:02d}/{TOTAL_SLIDES:02d}</text>
</svg>
'''


def centered_end_page(slide_no):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720" role="img" aria-label="结束页">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#0B1020"/>
      <stop offset="55%" stop-color="#111827"/>
      <stop offset="100%" stop-color="#172033"/>
    </linearGradient>
    <style>
      .page {{ font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif; }}
      .small {{ fill: #94A3B8; font-size: 12.5px; font-weight: 520; letter-spacing: 0; }}
    </style>
  </defs>
  <rect class="page" width="1280" height="720" fill="url(#bg)"/>
  <circle cx="1126" cy="-88" r="282" fill="#2563EB" opacity="0.12"/>
  <circle cx="-86" cy="650" r="310" fill="#059669" opacity="0.10"/>
  <g class="page">
    <text x="640" y="310" text-anchor="middle" fill="#F8FAFC" font-size="54" font-weight="850">谢谢</text>
    <text x="640" y="374" text-anchor="middle" fill="#CBD5E1" font-size="24" font-weight="600">协程技术调研</text>
    {text_outline_path(STUDENT_INFO, 640, 424, 18, "#94A3B8")}
  </g>
  <text x="1232" y="692" text-anchor="end" class="small">{slide_no:02d}/{TOTAL_SLIDES:02d}</text>
</svg>
'''


def renumber_slide(content, index, total):
    return re.sub(
        r'(<text x="1232" y="692" text-anchor="end" class="small">)\d{2}/\d{2}(</text>)',
        rf'\g<1>{index:02d}/{total:02d}\2',
        content,
    )


summary = pd.read_csv(DATA_DIR / "协程技术调研-实验汇总.csv")
summary["series"] = summary.apply(
    lambda r: r["model"] if pd.isna(r["workers"]) else f"{r['model']}-{int(r['workers'])}",
    axis=1,
)
io5000 = summary[(summary["scenario"] == "tcp_io") & (summary["task_count"] == 5000)]
cpu200 = summary[(summary["scenario"] == "cpu_bound") & (summary["task_count"] == 200)]


def metric(series, col):
    return float(io5000[io5000["series"] == series][col].iloc[0])


async_dur = metric("asyncio", "duration_seconds_median")
th200_dur = metric("threads-200", "duration_seconds_median")
th200_threads = metric("threads-200", "peak_extra_python_threads_median")
async_threads = metric("asyncio", "peak_extra_python_threads_median")
async_rss = metric("asyncio", "peak_rss_delta_mb_median")
th200_rss = metric("threads-200", "peak_rss_delta_mb_median")


def _tcp_value(task_count, series, col):
    row = summary[(summary["scenario"] == "tcp_io") & (summary["task_count"] == task_count) & (summary["series"] == series)]
    return float(row[col].iloc[0])


def _cpu_value(task_count, series, col):
    row = summary[(summary["scenario"] == "cpu_bound") & (summary["task_count"] == task_count) & (summary["series"] == series)]
    return float(row[col].iloc[0])


def svg_thread_bar_chart(x, y, w, h):
    labels = ["asyncio", "threads-50", "threads-100", "threads-200"]
    values = [_tcp_value(5000, label, "peak_extra_python_threads_median") for label in labels]
    colors = ["#2563EB", "#CBD5E1", "#94A3B8", "#64748B"]
    left, right, top, bottom = x + 96, x + w - 42, y + 74, y + h - 76
    chart_h = bottom - top
    max_v = 220
    parts = [
        f'<text x="{x + 60}" y="{y + 36}" fill="#111827" font-size="21" font-weight="850">5000 TCP requests: thread pool buys speed with threads</text>',
        f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" stroke="#111827" stroke-width="1.2"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{bottom}" stroke="#111827" stroke-width="1.2"/>',
        f'<text x="{x + 26}" y="{y + 230}" transform="rotate(-90 {x + 26} {y + 230})" fill="#111827" font-size="14">Peak extra Python threads</text>',
    ]
    for tick in [0, 50, 100, 150, 200]:
        yy = bottom - tick / max_v * chart_h
        parts.append(f'<line x1="{left}" y1="{yy:.1f}" x2="{right}" y2="{yy:.1f}" stroke="#E5E7EB" stroke-width="1"/>')
        parts.append(f'<text x="{left - 12}" y="{yy + 5:.1f}" text-anchor="end" fill="#111827" font-size="12">{tick}</text>')
    slot = (right - left) / len(labels)
    bar_w = 112
    for index, (label, value, color) in enumerate(zip(labels, values, colors)):
        cx = left + slot * index + slot / 2
        bar_h = value / max_v * chart_h
        bx = cx - bar_w / 2
        by = bottom - bar_h
        parts.append(f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bar_w}" height="{bar_h:.1f}" rx="3" fill="{color}"/>')
        parts.append(f'<text x="{cx:.1f}" y="{by - 8:.1f}" text-anchor="middle" fill="#111827" font-size="12">{value:.0f}</text>')
        parts.append(f'<text x="{cx:.1f}" y="{bottom + 26}" text-anchor="middle" fill="#111827" font-size="12">{label}</text>')
    return "\n".join(parts)


def svg_scaling_line_chart(x, y, w, h):
    task_counts = [100, 500, 1000, 3000, 5000]
    series = [
        ("asyncio", "#2563EB"),
        ("threads-200", "#64748B"),
    ]
    values = {
        label: [_tcp_value(task_count, label, "duration_seconds_median") for task_count in task_counts]
        for label, _ in series
    }
    left, right, top, bottom = x + 86, x + w - 48, y + 74, y + h - 78
    max_x = max(task_counts)
    max_y = 5.0
    parts = [
        f'<text x="{x + 54}" y="{y + 36}" fill="#111827" font-size="21" font-weight="850">Scaling: compare the best thread pool against asyncio</text>',
        f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" stroke="#111827" stroke-width="1.2"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{bottom}" stroke="#111827" stroke-width="1.2"/>',
        f'<text x="{x + 24}" y="{y + 230}" transform="rotate(-90 {x + 24} {y + 230})" fill="#111827" font-size="14">Median duration (s)</text>',
        f'<text x="{x + w / 2}" y="{bottom + 54}" text-anchor="middle" fill="#111827" font-size="13">TCP request count</text>',
    ]
    for tick in [0, 1, 2, 3, 4, 5]:
        yy = bottom - tick / max_y * (bottom - top)
        parts.append(f'<line x1="{left}" y1="{yy:.1f}" x2="{right}" y2="{yy:.1f}" stroke="#E5E7EB" stroke-width="1"/>')
        parts.append(f'<text x="{left - 12}" y="{yy + 5:.1f}" text-anchor="end" fill="#111827" font-size="12">{tick}</text>')
    for tick in task_counts:
        xx = left + tick / max_x * (right - left)
        parts.append(f'<text x="{xx:.1f}" y="{bottom + 24}" text-anchor="middle" fill="#111827" font-size="11">{tick}</text>')
    legend_x = left + 12
    for i, (label, color) in enumerate(series):
        ly = top + 18 + i * 24
        parts.append(f'<line x1="{legend_x}" y1="{ly}" x2="{legend_x + 24}" y2="{ly}" stroke="{color}" stroke-width="4" stroke-linecap="round"/>')
        parts.append(f'<circle cx="{legend_x + 12}" cy="{ly}" r="4" fill="{color}"/>')
        parts.append(f'<text x="{legend_x + 36}" y="{ly + 5}" fill="#111827" font-size="12">{label}</text>')
    for label, color in series:
        points = []
        for task_count, value in zip(task_counts, values[label]):
            xx = left + task_count / max_x * (right - left)
            yy = bottom - value / max_y * (bottom - top)
            points.append((xx, yy))
        point_attr = " ".join(f"{xx:.1f},{yy:.1f}" for xx, yy in points)
        parts.append(f'<polyline points="{point_attr}" fill="none" stroke="{color}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>')
        for xx, yy in points:
            parts.append(f'<circle cx="{xx:.1f}" cy="{yy:.1f}" r="4.5" fill="{color}"/>')
    return "\n".join(parts)


def svg_cpu_norm_chart(x, y, w, h):
    labels = ["asyncio", "threads-50", "threads-100", "threads-200"]
    base = _cpu_value(200, "asyncio", "duration_seconds_median")
    values = [_cpu_value(200, label, "duration_seconds_median") / base for label in labels]
    colors = ["#2563EB", "#CBD5E1", "#94A3B8", "#64748B"]
    left, right, top, bottom = x + 86, x + w - 42, y + 74, y + h - 76
    chart_h = bottom - top
    max_v = 1.1
    parts = [
        f'<text x="{x + 54}" y="{y + 36}" fill="#111827" font-size="21" font-weight="850">200 CPU tasks: coroutine does not create CPU parallelism</text>',
        f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" stroke="#111827" stroke-width="1.2"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{bottom}" stroke="#111827" stroke-width="1.2"/>',
        f'<text x="{x + 24}" y="{y + 230}" transform="rotate(-90 {x + 24} {y + 230})" fill="#111827" font-size="14">Normalized duration (asyncio = 1.0)</text>',
    ]
    for tick in [0, 0.2, 0.4, 0.6, 0.8, 1.0]:
        yy = bottom - tick / max_v * chart_h
        parts.append(f'<line x1="{left}" y1="{yy:.1f}" x2="{right}" y2="{yy:.1f}" stroke="#E5E7EB" stroke-width="1"/>')
        parts.append(f'<text x="{left - 12}" y="{yy + 5:.1f}" text-anchor="end" fill="#111827" font-size="12">{tick:.1f}</text>')
    slot = (right - left) / len(labels)
    bar_w = 116
    for index, (label, value, color) in enumerate(zip(labels, values, colors)):
        cx = left + slot * index + slot / 2
        bar_h = value / max_v * chart_h
        bx = cx - bar_w / 2
        by = bottom - bar_h
        parts.append(f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bar_w}" height="{bar_h:.1f}" rx="3" fill="{color}"/>')
        parts.append(f'<text x="{cx:.1f}" y="{by - 8:.1f}" text-anchor="middle" fill="#111827" font-size="12">{value:.2f}×</text>')
        parts.append(f'<text x="{cx:.1f}" y="{bottom + 26}" text-anchor="middle" fill="#111827" font-size="12">{label}</text>')
    return "\n".join(parts)

slides = [centered_title_page(1)]

slides.append(page(1, "PARALLEL PROGRAMMING · COROUTINE RESEARCH", "协程技术调研", "从线程瓶颈、运行时机制、语言路线到本地 TCP I/O 实验验证", f'''
    <rect x="48" y="156" width="1184" height="470" rx="30" class="card2"/>
    <text x="96" y="218" class="h1">协程的核心价值：降低 I/O 等待的线程占用</text>
    <text x="100" y="268" class="body2">本报告围绕等待任务的调度机制、资源代价和工程边界展开，并用本地 TCP I/O 与 CPU-bound 实验校验结论。</text>
    <g transform="translate(96 316)">
      <rect x="0" y="0" width="318" height="168" rx="20" fill="rgba(220,38,38,0.17)" stroke="rgba(248,113,113,0.32)"/>
      <text x="26" y="38" class="kicker">PROBLEM</text>
      <text x="26" y="76" class="h2">线程瓶颈</text>
      <text x="26" y="112" class="small">大量请求卡在 DB / RPC / 网络等待；</text>
      <text x="26" y="138" class="small">线程仍占栈、调度和上下文切换成本。</text>
      <rect x="350" y="0" width="318" height="168" rx="20" fill="rgba(37,99,235,0.20)" stroke="rgba(96,165,250,0.36)"/>
      <text x="376" y="38" class="kicker">MECHANISM</text>
      <text x="376" y="76" class="h2">状态保存 + 事件恢复</text>
      <text x="376" y="112" class="small">await 挂起协程帧，把线程还给运行时；</text>
      <text x="376" y="138" class="small">事件就绪后从 continuation 恢复。</text>
      <rect x="700" y="0" width="318" height="168" rx="20" fill="rgba(5,150,105,0.20)" stroke="rgba(52,211,153,0.36)"/>
      <text x="726" y="38" class="kicker">EVIDENCE</text>
      <text x="726" y="76" class="h2">5000 TCP 请求</text>
      <text x="726" y="112" class="small">asyncio 0线程；threads-200约200。</text>
      <text x="726" y="138" class="small">CPU 算力仍取决于并行计算方案。</text>
    </g>
    <g transform="translate(96 526)">
      {pill(0, 0, 120, "线程瓶颈", "#DC2626")}
      {pill(148, 0, 132, "事件驱动", "#059669")}
      {pill(308, 0, 120, "协程抽象", "#2563EB")}
      {pill(456, 0, 132, "运行时调度", "#7C3AED")}
      {pill(616, 0, 132, "实验验证", "#64748B")}
    </g>
''')) 

slides.append(page(2, "PROBLEM", "高并发服务为什么卡在等待", "请求常在网络、数据库、RPC、缓存、消息队列、定时器或锁上等待；等待期间线程资源仍被占用。", f'''
    {card(48, 158, 760, 470, "card2", "#2563EB")}
    <text x="82" y="204" class="kicker">REQUEST LIFECYCLE</text>
    <text x="82" y="244" class="h2">高并发请求的主要矛盾：短计算片段叠加长外部等待</text>
    <rect x="82" y="276" width="688" height="94" rx="16" fill="rgba(255,255,255,0.08)" stroke="rgba(255,255,255,0.16)"/>
    <text x="108" y="310" class="body">报告原文口径：一个请求的大部分时间花在等待外部事件上。</text>
    <text x="108" y="340" class="small">阻塞等待期间，线程本身没有执行有意义的计算；线程栈、调度上下文和内核对象仍然存在。</text>
    <g transform="translate(88 420)">
      <rect x="0" y="0" width="96" height="44" rx="11" fill="#2563EB"/><text x="48" y="28" text-anchor="middle" fill="#fff" font-size="15" font-weight="850">CPU</text>
      <rect x="116" y="0" width="422" height="44" rx="11" fill="rgba(255,255,255,0.12)" stroke="rgba(255,255,255,0.20)"/><text x="327" y="28" text-anchor="middle" class="small">等待 DB / RPC / 网络 / 限流器</text>
      <rect x="558" y="0" width="96" height="44" rx="11" fill="#2563EB"/><text x="606" y="28" text-anchor="middle" fill="#fff" font-size="15" font-weight="850">CPU</text>
      <text x="0" y="96" class="body">线程模型：等待期间仍占一个 OS 线程，资源开销随并发放大</text>
      <text x="0" y="130" class="body">协程模型：任务挂起进入运行时队列，线程继续处理其他可运行任务</text>
      <text x="0" y="164" class="small">选型判断：先确认瓶颈在等待、连接池、下游容量还是 CPU 计算。</text>
    </g>
    {card(832, 158, 400, 220, "card", "#059669")}
    <text x="862" y="204" class="kicker">WAIT SOURCES</text>
    {bullets(862, 244, ["客户端网络包到达", "数据库 / Redis / 消息队列", "RPC 下游响应", "磁盘、对象存储、文件系统", "连接池、限流器、定时器、锁"], 30)}
    {card(832, 398, 400, 230, "card", "#DC2626")}
    <text x="862" y="444" class="kicker">WHY IT MATTERS</text>
    <text x="862" y="506" class="metric">10K+</text>
    <text x="1000" y="486" class="body">连接同时等待时</text>
    <text x="1000" y="516" class="body">线程栈、内核对象</text>
    <text x="1000" y="546" class="body">和调度上下文会放大成本</text>
    <text x="862" y="590" class="small">C10K 推动了事件驱动、非阻塞 I/O、</text>
    <text x="862" y="614" class="small">异步框架与协程运行时的发展。</text>
''')) 

slides.append(page(3, "EVOLUTION", "并发模型一步步降低等待成本", "从进程到线程，再到事件循环与协程，演进目标是降低等待资源占用，同时保留代码可维护性。", f'''
    {card(48, 158, 1184, 144, "card2", "#2563EB")}
    <text x="82" y="210" class="h2">协程处在事件驱动高吞吐与顺序代码可读性之间</text>
    <text x="82" y="250" class="body">报告原文口径：先看任务瓶颈，再选抽象；CPU 密集、强隔离、I/O 等待和传统同步迁移对应不同方案。</text>
    <text x="82" y="282" class="small">判断维度：隔离强度、上下文切换、内存占用、状态管理复杂度、生态是否支持非阻塞 I/O。</text>
    {card(48, 326, 216, 232, "card", "#64748B")}
    <text x="78" y="374" class="h3">进程</text>
    <text x="78" y="414" class="body">隔离强</text>
    <text x="78" y="446" class="small">崩溃影响小</text>
    <text x="78" y="474" class="small">创建和切换成本高</text>
    <text x="78" y="502" class="small">适合强隔离任务</text>
    <text x="78" y="530" class="small">高并发连接成本偏重</text>
    {card(284, 326, 216, 232, "card", "#DC2626")}
    <text x="314" y="374" class="h3">线程</text>
    <text x="314" y="414" class="body">代码直观</text>
    <text x="314" y="446" class="small">共享内存方便</text>
    <text x="314" y="474" class="small">等待也占 OS 线程</text>
    <text x="314" y="502" class="small">栈内存与调度开销放大</text>
    <text x="314" y="530" class="small">适合中等并发与阻塞生态</text>
    {card(520, 326, 216, 232, "card", "#059669")}
    <text x="550" y="374" class="h3">事件循环</text>
    <text x="550" y="414" class="body">少线程高吞吐</text>
    <text x="550" y="446" class="small">依赖非阻塞 I/O</text>
    <text x="550" y="474" class="small">回调链容易分散状态</text>
    <text x="550" y="502" class="small">适合连接数很高场景</text>
    <text x="550" y="530" class="small">可维护性需要额外设计</text>
    {card(756, 326, 216, 232, "card2", "#2563EB")}
    <text x="786" y="374" class="h3">协程</text>
    <text x="786" y="414" class="body">顺序代码表达等待</text>
    <text x="786" y="446" class="small">状态由协程帧保存</text>
    <text x="786" y="474" class="small">运行时负责排队恢复</text>
    <text x="786" y="502" class="small">适合 I/O 等待占主导</text>
    <text x="786" y="530" class="small">阻塞调用会破坏调度</text>
    {card(992, 326, 240, 232, "card", "#7C3AED")}
    <text x="1022" y="374" class="h3">虚拟线程</text>
    <text x="1022" y="414" class="body">接近线程心智</text>
    <text x="1022" y="446" class="small">JVM 调度到平台线程</text>
    <text x="1022" y="474" class="small">迁移同步代码成本低</text>
    <text x="1022" y="502" class="small">需关注 pinning</text>
    <text x="1022" y="530" class="small">下游容量仍需限流</text>
''')) 

slides.append(page(4, "ABSTRACTION", "事件循环到协程：把性能重新包装成可读代码", "协程同时服务两个目标：保持事件驱动的资源效率，降低异步代码的状态管理成本。", f'''
    {card(48, 166, 360, 392, "card", "#DC2626")}
    <text x="78" y="210" class="kicker">THREAD STYLE</text><text x="78" y="250" class="h2">同步线程式代码</text>
    {bullets(78, 304, ["调用链直观", "等待也占线程", "高并发资源成本高"], 34, "body", "#F87171")}
    <rect x="78" y="430" width="300" height="72" rx="15" fill="rgba(255,255,255,0.08)"/><text x="104" y="462" class="small">data = read()</text><text x="104" y="488" class="small">return parse(data)</text>
    {card(460, 166, 360, 392, "card", "#059669")}
    <text x="490" y="210" class="kicker">EVENT LOOP</text><text x="490" y="250" class="h2">事件循环回调</text>
    {bullets(490, 304, ["少线程高吞吐", "回调链复杂", "状态分散"], 34, "body", "#34D399")}
    <rect x="490" y="430" width="300" height="72" rx="15" fill="rgba(255,255,255,0.08)"/><text x="516" y="462" class="small">read(on_done)</text><text x="516" y="488" class="small">on_done -> parse()</text>
    {card(872, 166, 360, 392, "card2", "#2563EB")}
    <text x="902" y="210" class="kicker">COROUTINE</text><text x="902" y="250" class="h2">async / await 协程</text>
    {bullets(902, 304, ["等待不独占线程", "代码按流程阅读", "运行时恢复执行"], 34, "body", "#60A5FA")}
    <rect x="902" y="430" width="300" height="72" rx="15" fill="rgba(37,99,235,0.22)" stroke="rgba(96,165,250,0.36)"/><text x="928" y="462" class="small">data = await read()</text><text x="928" y="488" class="small">return parse(data)</text>
'''))

slides.append(page(5, "DEFINITION", "协程是可暂停、可恢复的函数", "核心机制是在挂起点保存现场、释放线程，并在事件就绪后继续执行。", f'''
    {card(48, 166, 730, 392, "card2", "#2563EB")}
    <text x="82" y="210" class="kicker">EXECUTION TRACK</text><text x="82" y="250" class="h2">普通函数连续执行；协程在 await 点保存现场</text>
    <g transform="translate(92 330)">
      <text x="0" y="0" class="body">普通函数</text><path d="M128 -6 L604 -6" stroke="#94A3B8" stroke-width="8" stroke-linecap="round"/>
      <text x="0" y="94" class="body">协程函数</text><path d="M128 88 L264 88" stroke="#60A5FA" stroke-width="8" stroke-linecap="round"/><path d="M350 88 L500 88" stroke="#60A5FA" stroke-width="8" stroke-linecap="round"/><path d="M566 88 L604 88" stroke="#60A5FA" stroke-width="8" stroke-linecap="round"/>
      <circle cx="264" cy="88" r="13" fill="#2563EB"/><text x="238" y="130" class="small">await I/O</text><circle cx="500" cy="88" r="13" fill="#2563EB"/><text x="478" y="130" class="small">恢复</text>
    </g>
    {card(804, 166, 428, 178, "card", "#059669")}
    <text x="834" y="208" class="kicker">STATE SAVED</text>
    {bullets(834, 248, ["局部变量", "下一步执行位置", "返回值与异常", "恢复句柄 / continuation"], 28)}
    {card(804, 364, 428, 194, "card", "#DC2626")}
    <text x="834" y="406" class="kicker">BOUNDARY</text>
    <text x="834" y="448" class="h2">CPU 并行需要独立方案</text>
    <text x="834" y="486" class="body">协程降低等待占用，</text>
    <text x="834" y="516" class="body">CPU 算力仍取决于多核与计算后端。</text>
'''))

slides.append(page(6, "IMPLEMENTATION TYPES", "Stackless 与 Stackful：两种协程实现心智", "实现方式决定了语言的侵入性、运行时复杂度和调试体验。", f'''
    {card(48, 166, 560, 392, "card2", "#2563EB")}
    <text x="82" y="210" class="kicker">STACKLESS</text><text x="82" y="250" class="h2">编译器拆成状态机</text>
    {bullets(82, 306, ["不保存完整调用栈", "局部变量进入协程帧", "await 沿调用链显式传播", "代表：C++20、Python、C#"], 34)}
    {card(648, 166, 584, 392, "card", "#7C3AED")}
    <text x="682" y="210" class="kicker">STACKFUL / FIBER-LIKE</text><text x="682" y="250" class="h2">每个轻量执行单元保留自己的栈语义</text>
    {bullets(682, 306, ["更接近线程式心智", "调用链侵入性较低", "栈管理和调度更复杂", "代表：部分fiber库、虚拟线程内部思路"], 34, "body", "#C4B5FD")}
'''))

slides.append(page(7, "STATE MACHINE", "协程底层是状态保存、排队与恢复", "await 触发保存现场、注册等待、让出线程，并在事件就绪后恢复执行。", f'''
    {card(48, 154, 1184, 502, "card2", "#2563EB")}
    <text x="82" y="196" class="kicker">COROUTINE LOWERING</text>

    <rect x="82" y="224" width="318" height="220" rx="18" fill="rgba(15,23,42,0.82)" stroke="rgba(255,255,255,0.18)"/>
    <text x="110" y="260" class="small">async def fetch():</text>
    <text x="110" y="292" class="small">    conn = await open()</text>
    <text x="110" y="324" class="small">    data = await read(conn)</text>
    <text x="110" y="356" class="small">    return parse(data)</text>
    <line x1="110" y1="378" x2="370" y2="378" stroke="rgba(255,255,255,0.16)"/>
    <text x="110" y="406" class="small">await 是可暂停点；普通函数调用</text>
    <text x="110" y="430" class="small">会继续占用当前调用栈。</text>

    <path d="M420 328 L464 328" class="line" stroke="#64748B"/>
    <polygon points="464,328 446,317 446,339" fill="#64748B"/>

    <rect x="484" y="206" width="380" height="264" rx="22" fill="rgba(37,99,235,0.20)" stroke="rgba(96,165,250,0.42)" stroke-width="1.4"/>
    <text x="520" y="244" class="kicker">COROUTINE FRAME</text>
    <text x="520" y="274" class="small">挂起时保存到堆上的运行时对象</text>
    <rect x="520" y="296" width="308" height="32" rx="10" fill="rgba(15,23,42,0.72)" stroke="rgba(255,255,255,0.16)"/>
    <text x="540" y="318" class="small">locals：conn / data / 临时变量</text>
    <rect x="520" y="338" width="308" height="32" rx="10" fill="rgba(15,23,42,0.72)" stroke="rgba(255,255,255,0.16)"/>
    <text x="540" y="360" class="small">state：下一条待执行指令</text>
    <rect x="520" y="380" width="308" height="32" rx="10" fill="rgba(15,23,42,0.72)" stroke="rgba(255,255,255,0.16)"/>
    <text x="540" y="402" class="small">slot：返回值 / 异常传播</text>
    <rect x="520" y="422" width="308" height="32" rx="10" fill="rgba(15,23,42,0.72)" stroke="rgba(255,255,255,0.16)"/>
    <text x="540" y="444" class="small">continuation：恢复入口</text>

    <path d="M884 328 L928 328" class="line" stroke="#64748B"/>
    <polygon points="928,328 910,317 910,339" fill="#64748B"/>

    <rect x="948" y="214" width="246" height="246" rx="22" fill="rgba(255,255,255,0.08)" stroke="rgba(255,255,255,0.18)"/>
    <text x="978" y="252" class="kicker">RUNTIME QUEUES</text>
    <text x="978" y="292" class="body">1. awaiter 注册等待</text>
    <text x="978" y="326" class="body">2. 任务让出线程</text>
    <text x="978" y="360" class="body">3. 就绪后进队列</text>
    <text x="978" y="394" class="body">4. event loop 恢复</text>
    <text x="978" y="430" class="small">线程继续处理其他可运行任务。</text>

    <rect x="82" y="500" width="360" height="108" rx="18" fill="rgba(5,150,105,0.18)" stroke="rgba(52,211,153,0.34)"/>
    <text x="110" y="536" class="h3">控制权发生了什么？</text>
    <text x="110" y="570" class="body">保存现场 → 返回事件循环</text>
    <text x="110" y="594" class="small">调度其他可运行任务。</text>
    <rect x="472" y="500" width="360" height="108" rx="18" fill="rgba(124,58,237,0.18)" stroke="rgba(196,181,253,0.34)"/>
    <text x="500" y="536" class="h3">数据结构发生了什么？</text>
    <text x="500" y="570" class="body">协程帧记录 locals / state</text>
    <text x="500" y="594" class="small">同时保存 slot 与 continuation。</text>
    <rect x="862" y="500" width="328" height="108" rx="18" fill="rgba(37,99,235,0.20)" stroke="rgba(96,165,250,0.36)"/>
    <text x="890" y="536" class="h3">一句话结论</text>
    <text x="890" y="570" class="body">await = 保存现场 + 让出线程</text>
    <text x="890" y="594" class="small">事件就绪后从恢复入口继续执行。</text>
''')) 

slides.append(page(8, "SYSTEM", "编译器、运行时、OS 如何协同", "操作系统调度线程，运行时调度协程；协程没有脱离线程存在。", f'''
    {card(48, 166, 780, 392, "card2", "#2563EB")}
    <text x="82" y="208" class="kicker">LAYERED ARCHITECTURE</text>
    <g transform="translate(86 248)">
      <rect x="0" y="0" width="680" height="56" rx="16" fill="rgba(37,99,235,0.22)" stroke="rgba(96,165,250,0.36)"/><text x="24" y="36" class="body2">应用代码：async/await · goroutine · virtual thread</text>
      <rect x="0" y="76" width="680" height="56" rx="16" fill="rgba(255,255,255,0.08)" stroke="rgba(255,255,255,0.16)"/><text x="24" y="112" class="body2">语言 / 编译器：协程帧 · 状态机 · continuation</text>
      <rect x="0" y="152" width="680" height="56" rx="16" fill="rgba(5,150,105,0.23)" stroke="rgba(52,211,153,0.36)"/><text x="24" y="188" class="body2">运行时：event loop · scheduler · ready queue</text>
      <rect x="0" y="228" width="680" height="56" rx="16" fill="rgba(220,38,38,0.20)" stroke="rgba(248,113,113,0.35)"/><text x="24" y="264" class="body2">操作系统：OS threads · epoll/kqueue/IOCP · I/O</text>
    </g>
    {card(852, 166, 380, 180, "card", "#059669")}
    <text x="882" y="208" class="kicker">KEY POINT</text><text x="882" y="252" class="h2">协程仍运行在线程上</text><text x="882" y="290" class="body">区别在于等待时不独占线程。</text>
    {card(852, 366, 380, 192, "card", "#64748B")}
    <text x="882" y="408" class="kicker">OS EVENTS</text>{bullets(882, 446, ["Linux epoll", "BSD/macOS kqueue", "Windows IOCP", "libuv 跨平台封装"], 30)}
'''))

slides.append(page(9, "LANGUAGE ROUTES", "主流语言走向两条降低异步复杂度的路线", "显式 async/await 与轻量线程化并存，目标都是降低等待成本。", f'''
    {card(48, 166, 548, 392, "card2", "#2563EB")}
    <text x="82" y="210" class="kicker">ROUTE A</text><text x="82" y="252" class="h2">显式 async / await</text>
    <text x="82" y="294" class="body">代表：Python、C#、C++ coroutine 生态</text>
    {bullets(82, 342, ["调用链显式异步", "编译器/解释器生成状态机", "适合 I/O API 已异步化的生态", "风险：阻塞调用破坏调度"], 32)}
    {card(636, 166, 596, 392, "card", "#7C3AED")}
    <text x="670" y="210" class="kicker">ROUTE B</text><text x="670" y="252" class="h2">轻量线程化抽象</text>
    <text x="670" y="294" class="body">代表：Go goroutine、Java 21 Virtual Threads</text>
    {bullets(670, 342, ["更接近“一任务一执行单元”的心智", "运行时把轻量任务映射到 OS 线程", "传统同步代码迁移成本更低", "边界：CPU密集、pinning、下游容量"], 32, "body", "#C4B5FD")}
'''))

slides.append(page(10, "LANGUAGES I", "C++、Go、Python：从底层机制到显式事件循环", "同样处理轻量并发，抽象层级和工程心智完全不同。", f'''
    {card(48, 166, 360, 392, "card", "#64748B")}
    <text x="78" y="210" class="kicker">C++20</text><text x="78" y="252" class="h2">底层机制</text>{bullets(78, 304, ["co_await / co_yield / co_return", "标准提供基础设施", "运行时与调度依赖库", "适合高性能系统框架"], 34)}
    {card(460, 166, 360, 392, "card2", "#059669")}
    <text x="490" y="210" class="kicker">GO</text><text x="490" y="252" class="h2">默认并发工具</text>{bullets(490, 304, ["go f() 启动 goroutine", "runtime 使用 M/P/G 调度", "channel 与 context 协作", "适合服务端高并发"], 34, "body", "#34D399")}
    {card(872, 166, 360, 392, "card", "#2563EB")}
    <text x="902" y="210" class="kicker">PYTHON</text><text x="902" y="252" class="h2">显式事件循环</text>{bullets(902, 304, ["async def / await", "Task 排入 event loop", "TaskGroup 支持结构化并发", "阻塞调用会卡住事件循环"], 34)}
'''))

slides.append(page(11, "LANGUAGES II", "C# 与 Java：应用异步和虚拟线程的工程路线", "成熟运行时把复杂调度隐藏在 Task 或 Virtual Thread 后面。", f'''
    {card(48, 166, 560, 392, "card2", "#2563EB")}
    <text x="82" y="210" class="kicker">C# ASYNC/AWAIT</text><text x="82" y="252" class="h2">围绕 Task 的应用层异步模型</text>
    {bullets(82, 306, ["编译器生成状态机", "Task / Task<T> 表示异步结果", "生态中 HTTP、DB、UI 等API广泛支持", "避免 .Result / .Wait() 阻塞"], 34)}
    {card(648, 166, 584, 392, "card", "#7C3AED")}
    <text x="682" y="210" class="kicker">JAVA 21 VIRTUAL THREADS</text><text x="682" y="252" class="h2">让同步线程式代码重新可扩展</text>
    {bullets(682, 306, ["JVM调度虚拟线程到平台线程", "阻塞I/O时可卸载承载线程", "迁移传统thread-per-request更容易", "关注pinning与下游资源上限"], 34, "body", "#C4B5FD")}
'''))

slides.append(page(12, "EXPERIMENT DESIGN", "实验设计：本地真实 TCP I/O + CPU 边界", "主实验采用本地 socket 读写和服务端等待，旧 sleep 模拟仅作为概念补充材料。", f'''
    {card(48, 166, 710, 392, "card2", "#2563EB")}
    <text x="82" y="208" class="kicker">MATRIX</text>
    <rect x="82" y="238" width="636" height="254" rx="18" fill="rgba(255,255,255,0.08)" stroke="rgba(255,255,255,0.16)"/>
    <text x="112" y="282" class="h3">场景</text><text x="260" y="282" class="h3">asyncio</text><text x="436" y="282" class="h3">threads</text><text x="588" y="282" class="h3">指标</text>
    <line x1="104" y1="304" x2="696" y2="304" class="axis"/>
    <text x="112" y="344" class="body">TCP I/O</text><text x="260" y="344" class="small">open_connection</text><text x="436" y="344" class="small">blocking socket</text><text x="588" y="344" class="small">耗时/线程/RSS</text>
    <line x1="104" y1="372" x2="696" y2="372" class="axis"/>
    <text x="112" y="414" class="body">CPU 计算</text><text x="260" y="414" class="small">coroutine内循环</text><text x="436" y="414" class="small">线程池循环</text><text x="588" y="414" class="small">归一化耗时</text>
    <text x="82" y="528" class="small">TCP server: 127.0.0.1 动态端口；每次请求延迟 0.02s；重复5次。</text>
    {card(788, 166, 444, 176, "card", "#059669")}
    <text x="818" y="208" class="kicker">PARAMETERS</text>{bullets(818, 246, ["I/O请求数：100 到 5000", "asyncio连接上限：50", "线程池worker：50/100/200", "CPU任务数：50/100/200"], 29)}
    {card(788, 362, 444, 196, "card", "#DC2626")}
    <text x="818" y="404" class="kicker">WHY THIS IS BETTER</text>{bullets(818, 442, ["真实 socket 读写", "明细与汇总数据分离", "RSS和线程采样", "旧sleep实验降为补充"], 29, "body", "#F87171")}
'''))

slides.append(page(13, "METRICS", "实验指标解释：主读中位数，补充看均值和范围", "指标口径先讲清楚，实验结论才不会被误读。", f'''
    {card(48, 166, 370, 392, "card2", "#2563EB")}
    <text x="82" y="210" class="kicker">TIME</text><text x="82" y="252" class="h2">中位耗时</text>{bullets(82, 306, ["每组重复5次", "主读median，降低偶然波动", "PDF保留mean/min/max"], 34)}
    {card(456, 166, 370, 392, "card", "#059669")}
    <text x="490" y="210" class="kicker">RESOURCE</text><text x="490" y="252" class="h2">业务新增线程 + RSS增量</text>{bullets(490, 306, ["线程数扣除server和sampler基线", "RSS来自psutil采样", "tracemalloc仅作为补充"], 34, "body", "#34D399")}
    {card(864, 166, 368, 392, "card", "#DC2626")}
    <text x="898" y="210" class="kicker">LIMITATION</text><text x="898" y="252" class="h2">实验边界</text>{bullets(898, 306, ["loopback不等于公网生产环境", "Python结果只代表本实验", "CPU实验受GIL影响", "结论聚焦模型边界"], 34, "body", "#F87171")}
'''))

slides.append(page(14, "I/O RESULT", "I/O结果：线程池更快，但用线程换速度", "asyncio用0个业务新增线程稳定承载5000个TCP请求；threads-200更快，但新增约200个线程。", f'''
    <rect x="48" y="166" width="900" height="392" rx="22" class="chartcard"/>
    {svg_thread_bar_chart(66, 186, 864, 348)}
    {card(976, 166, 256, 392, "card", "#2563EB")}
    <text x="1006" y="210" class="kicker">KEY DATA</text>
    <text x="1006" y="262" class="metric">0 vs {th200_threads:.0f}</text>
    <text x="1006" y="296" class="body">业务新增线程</text>
    <line x1="1006" y1="326" x2="1190" y2="326" class="axis"/>
    <text x="1006" y="370" class="h2">{async_dur:.2f}s</text>
    <text x="1092" y="370" class="body">asyncio</text>
    <text x="1006" y="414" class="h2">{th200_dur:.2f}s</text>
    <text x="1092" y="414" class="body">threads-200</text>
    <text x="1006" y="476" class="small">线程池用更多线程换低延迟；</text>
    <text x="1006" y="502" class="small">协程在低线程成本下承载并发。</text>
'''))

slides.append(page(15, "I/O SCALING", "扩展性与倍率：线程池用资源换延迟，协程用少线程换承载能力", "两张图分开回答“谁更快”和“代价是什么”。", f'''
    <rect x="48" y="166" width="900" height="392" rx="22" class="chartcard"/>
    {svg_scaling_line_chart(66, 186, 864, 348)}
    {card(976, 166, 256, 392, "card", "#7C3AED")}
    <text x="1006" y="210" class="kicker">RATIO @ 5000</text>
    <text x="1006" y="262" class="metric">{th200_dur / async_dur:.2f}×</text>
    <text x="1006" y="296" class="body">耗时倍率</text>
    <line x1="1006" y1="326" x2="1190" y2="326" class="axis"/>
    <text x="1006" y="370" class="h2">{th200_threads:.0f}</text>
    <text x="1078" y="370" class="body">新增线程</text>
    <text x="1006" y="414" class="h2">{th200_rss / max(async_rss, 0.01):.1f}×</text>
    <text x="1078" y="414" class="body">RSS增量倍率</text>
    <text x="1006" y="484" class="small">速度、线程数、内存增量</text>
    <text x="1006" y="510" class="small">必须一起读。</text>
'''))

slides.append(page(16, "CPU RESULT", "CPU结果：算力瓶颈需要并行计算方案", "CPU-bound 场景下，各模型归一化耗时接近；协程主要负责组织等待任务。", f'''
    <rect x="48" y="166" width="900" height="392" rx="22" class="chartcard"/>
    {svg_cpu_norm_chart(66, 186, 864, 348)}
    {card(976, 166, 256, 392, "card", "#DC2626")}
    <text x="1006" y="210" class="kicker">TAKEAWAY</text>
    <text x="1006" y="252" class="h2">等待交给协程</text>
    <text x="1006" y="284" class="h2">计算交给并行</text>
    {bullets(1006, 342, ["移出事件循环", "进程池/原生扩展", "向量化/SIMD/GPU", "别把协程当算力"], 34, "body", "#F87171")}
'''))

slides.append(page(17, "ENGINEERING RULES", "工程选型：先判断瓶颈，再选择模型", "选型必须同时看瓶颈类型、依赖库是否非阻塞、下游容量和取消/超时治理。", f'''
    {card(48, 158, 560, 426, "card2", "#2563EB")}
    <text x="82" y="208" class="kicker">DECISION TREE</text>
    <g transform="translate(96 252)">
      <rect x="0" y="0" width="460" height="56" rx="16" class="node"/><text x="230" y="36" text-anchor="middle" class="body2">瓶颈是否主要来自 I/O 等待？</text>
      <path d="M230 58 L230 92" class="line" stroke="#64748B"/>
      <rect x="-4" y="96" width="220" height="64" rx="16" fill="rgba(37,99,235,0.24)" stroke="rgba(96,165,250,0.35)"/><text x="106" y="136" text-anchor="middle" class="body">是：协程 / 异步I/O</text>
      <rect x="244" y="96" width="220" height="64" rx="16" fill="rgba(220,38,38,0.20)" stroke="rgba(248,113,113,0.35)"/><text x="354" y="136" text-anchor="middle" class="body">否：并行计算方案</text>
      <path d="M106 162 L106 196" class="line" stroke="#64748B"/><rect x="-4" y="200" width="220" height="64" rx="16" fill="rgba(5,150,105,0.22)" stroke="rgba(52,211,153,0.35)"/><text x="106" y="240" text-anchor="middle" class="body">加超时、限流、取消</text>
      <text x="0" y="308" class="small">补充判断：依赖库是否 awaitable？连接池/线程池是否限制下游并发？</text>
      <text x="0" y="334" class="small">取消是否能向下游传播？</text>
    </g>
    {card(632, 158, 284, 426, "card", "#059669")}
    <text x="662" y="208" class="kicker">USE WHEN</text>{bullets(662, 250, ["高并发Web服务", "RPC/API聚合", "爬虫与批量请求", "数据库与缓存访问", "长连接与定时器"], 34, "body", "#34D399")}
    <text x="662" y="446" class="small">落地要求：超时、背压、取消传播，</text>
    <text x="662" y="472" class="small">保留可观测性指标。</text>
    {card(948, 158, 284, 426, "card", "#DC2626")}
    <text x="978" y="208" class="kicker">AVOID WHEN</text>{bullets(978, 250, ["纯CPU计算", "大量阻塞库", "强实时调度", "无界任务创建", "缺少下游限流"], 34, "body", "#F87171")}
    <text x="978" y="446" class="small">替代方案：进程池、原生扩展，</text>
    <text x="978" y="472" class="small">向量化或虚拟线程迁移。</text>
''')) 

slides.append(page(18, "FINAL TAKEAWAY", "总结：协程是等待任务的调度抽象，CPU计算依赖并行方案", "PPT讲结论链路，PDF保留完整调研、实验方法、数据解释、局限性与参考资料。", f'''
    {card(48, 158, 376, 426, "card2", "#2563EB")}
    <text x="82" y="208" class="kicker">WHAT WE PROVED</text>
    <text x="82" y="250" class="h2">实验结论</text>
    {bullets(82, 300, ["TCP I/O：asyncio 新增线程 0", "threads-200：约200线程换低耗时", "CPU-bound：耗时接近，需并行方案", "主读 median，PDF 保留范围"], 31)}
    {card(456, 158, 376, 426, "card", "#059669")}
    <text x="490" y="208" class="kicker">WHAT IT MEANS</text>
    <text x="490" y="250" class="h2">工程判断</text>
    {bullets(490, 300, ["I/O 等待多：优先考虑协程/异步I/O", "阻塞库多：先处理同步调用和连接池", "CPU 密集：进程池、原生扩展或向量化", "任何模型都不能替代限流、超时和取消"], 31, "body", "#34D399")}
    {card(864, 158, 368, 426, "card", "#64748B")}
    <text x="898" y="208" class="kicker">DELIVERABLES</text>
    <text x="898" y="250" class="h2">提交材料</text>
    {bullets(898, 300, ["20页课堂汇报PPT", "20页SVG设计源", "协程技术调研报告PDF", "实验代码、明细CSV、汇总CSV、JSON", "AI辅助说明与参考资料"], 31, "body", "#94A3B8")}
    <text x="898" y="512" class="small">参考：OpenJDK JEP 444 · Python asyncio</text>
    <text x="898" y="538" class="small">Go Effective Go · Microsoft async/await</text>
    <text x="898" y="562" class="small">C++ coroutines · Linux epoll</text>
''')) 

slides.append(centered_end_page(len(slides) + 1))

for stale in OUT.glob("slide_*.svg"):
    stale.unlink()
for index, content in enumerate(slides, start=1):
    (OUT / f"slide_{index:02d}.svg").write_text(renumber_slide(content, index, len(slides)), encoding="utf-8")

index_html = [
    "<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\"><title>协程技术调研最终SVG Slides</title>",
    "<style>body{margin:0;background:#0b1020;color:#e5e7eb;font-family:'Microsoft YaHei','Segoe UI',Arial,sans-serif}main{max-width:1320px;margin:0 auto;padding:28px}section{margin:0 0 36px}h1{font-size:28px}h2{font-size:16px;color:#94a3b8}img{width:100%;border-radius:18px;box-shadow:0 20px 50px rgba(0,0,0,.35);background:#111827}</style>",
    "</head><body><main><h1>协程技术调研最终SVG Slides</h1>",
]
for index in range(1, len(slides) + 1):
    name = f"slide_{index:02d}.svg"
    index_html.append(f"<section><h2>{name}</h2><img src=\"{name}\" alt=\"{name}\"></section>")
index_html.append("</main></body></html>")
(OUT / "index.html").write_text("\n".join(index_html), encoding="utf-8")

print(f"Generated {len(slides)} final SVG slides in {OUT}")
