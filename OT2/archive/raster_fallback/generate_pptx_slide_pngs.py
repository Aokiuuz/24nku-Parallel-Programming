from __future__ import annotations

import csv
import math
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
OUT = ROOT / "pptx_slide_images"
W, H = 1280, 720

FONT_DIR = Path("C:/Windows/Fonts")
FONT_REG = FONT_DIR / "msyh.ttc"
FONT_BOLD = FONT_DIR / "msyhbd.ttc"
FONT_LIGHT = FONT_DIR / "msyhl.ttc"

BG_TOP = (10, 16, 32)
BG_MID = (17, 24, 39)
BG_BOTTOM = (23, 32, 51)
WHITE = (248, 250, 252)
TEXT = (226, 232, 240)
MUTED = (148, 163, 184)
SUBTLE = (203, 213, 225)
BLUE = (37, 99, 235)
BLUE2 = (96, 165, 250)
GREEN = (5, 150, 105)
GREEN2 = (52, 211, 153)
RED = (220, 38, 38)
RED2 = (248, 113, 113)
PURPLE = (124, 58, 237)
AMBER = (245, 158, 11)
SLATE = (100, 116, 139)


def font(size: int, bold: bool = False, light: bool = False) -> ImageFont.FreeTypeFont:
    path = FONT_BOLD if bold else FONT_LIGHT if light else FONT_REG
    return ImageFont.truetype(str(path), size=size)


F = {
    "kicker": font(13, bold=True),
    "title": font(35, bold=True),
    "subtitle": font(16),
    "h1": font(52, bold=True),
    "h2": font(23, bold=True),
    "h3": font(18, bold=True),
    "body": font(16),
    "body_bold": font(16, bold=True),
    "body2": font(18, bold=True),
    "small": font(12),
    "code": ImageFont.truetype(str(FONT_DIR / "consola.ttf"), size=15) if (FONT_DIR / "consola.ttf").exists() else font(15),
    "code_small": ImageFont.truetype(str(FONT_DIR / "consola.ttf"), size=13) if (FONT_DIR / "consola.ttf").exists() else font(13),
    "metric": font(43, bold=True),
    "metric2": font(34, bold=True),
}


@dataclass
class Metric:
    duration: float = 0.0
    threads: float = 0.0
    rss: float = 0.0
    throughput: float = 0.0


def load_metrics() -> dict[str, Metric]:
    path = ROOT / "协程技术调研-实验汇总.csv"
    rows: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    out: dict[str, Metric] = {}
    for row in rows:
        scenario = row["scenario"]
        task_count = int(float(row["task_count"]))
        model = row["model"]
        workers = row.get("workers") or ""
        key = model if workers in ("", "nan", "NaN") else f"{model}-{int(float(workers))}"
        out[f"{scenario}:{task_count}:{key}"] = Metric(
            duration=float(row["duration_seconds_median"]),
            threads=float(row["peak_extra_python_threads_median"]),
            rss=float(row["peak_rss_delta_mb_median"]),
            throughput=float(row["throughput_tasks_per_second_median"]),
        )
    return out


METRICS = load_metrics()


def metric(scenario: str, task_count: int, key: str) -> Metric:
    return METRICS[f"{scenario}:{task_count}:{key}"]


def rgba(color: tuple[int, int, int], alpha: int = 255) -> tuple[int, int, int, int]:
    return (*color, alpha)


def text_size(draw: ImageDraw.ImageDraw, s: str, fnt: ImageFont.FreeTypeFont) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), s, font=fnt)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def wrap_text(draw: ImageDraw.ImageDraw, s: str, fnt: ImageFont.FreeTypeFont, max_w: int) -> list[str]:
    lines: list[str] = []
    for paragraph in str(s).split("\n"):
        if not paragraph:
            lines.append("")
            continue
        current = ""
        for ch in paragraph:
            trial = current + ch
            if text_size(draw, trial, fnt)[0] <= max_w or not current:
                current = trial
            else:
                lines.append(current.rstrip())
                current = ch.lstrip()
        if current:
            lines.append(current.rstrip())
    return lines


def draw_wrapped(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    s: str,
    fnt: ImageFont.FreeTypeFont,
    max_w: int,
    fill: tuple[int, int, int] = TEXT,
    line_gap: int = 8,
) -> int:
    x, y = xy
    line_h = text_size(draw, "国", fnt)[1] + line_gap
    for line in wrap_text(draw, s, fnt, max_w):
        draw.text((x, y), line, font=fnt, fill=fill)
        y += line_h
    return y


def gradient_background() -> Image.Image:
    img = Image.new("RGBA", (W, H), rgba(BG_TOP))
    px = img.load()
    for y in range(H):
        t = y / (H - 1)
        if t < 0.55:
            u = t / 0.55
            c = tuple(int(BG_TOP[i] * (1 - u) + BG_MID[i] * u) for i in range(3))
        else:
            u = (t - 0.55) / 0.45
            c = tuple(int(BG_MID[i] * (1 - u) + BG_BOTTOM[i] * u) for i in range(3))
        for x in range(W):
            px[x, y] = rgba(c)
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay, "RGBA")
    d.ellipse((860, -300, 1390, 230), fill=rgba(BLUE, 28))
    d.ellipse((-330, 430, 280, 1040), fill=rgba(GREEN, 24))
    d.ellipse((930, 515, 1355, 940), fill=rgba(PURPLE, 18))
    img.alpha_composite(overlay)
    return img


def card(
    img: Image.Image,
    box: tuple[int, int, int, int],
    accent: tuple[int, int, int] = BLUE,
    fill_alpha: int = 25,
    border_alpha: int = 42,
    radius: int = 22,
    accent_width: int = 6,
) -> None:
    d = ImageDraw.Draw(img, "RGBA")
    x, y, w, h = box
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow, "RGBA")
    sd.rounded_rectangle((x, y + 14, x + w, y + h + 14), radius=radius, fill=(0, 0, 0, 58))
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))
    img.alpha_composite(shadow)
    d.rounded_rectangle((x, y, x + w, y + h), radius=radius, fill=(255, 255, 255, fill_alpha), outline=(255, 255, 255, border_alpha), width=1)
    if accent_width:
        d.rounded_rectangle((x, y, x + accent_width, y + h), radius=accent_width // 2 + 1, fill=rgba(accent, 236))


def chart_card(img: Image.Image, box: tuple[int, int, int, int], path: Path, pad: int = 20) -> None:
    d = ImageDraw.Draw(img, "RGBA")
    x, y, w, h = box
    d.rounded_rectangle((x, y, x + w, y + h), radius=22, fill=(248, 250, 252, 250), outline=(255, 255, 255, 80), width=1)
    chart = Image.open(path).convert("RGBA")
    chart.thumbnail((w - 2 * pad, h - 2 * pad), Image.Resampling.LANCZOS)
    cx = x + (w - chart.width) // 2
    cy = y + (h - chart.height) // 2
    img.alpha_composite(chart, (cx, cy))


def pill(img: Image.Image, x: int, y: int, w: int, label: str, color: tuple[int, int, int], fnt: ImageFont.FreeTypeFont | None = None) -> None:
    fnt = fnt or F["small"]
    d = ImageDraw.Draw(img, "RGBA")
    d.rounded_rectangle((x, y, x + w, y + 31), radius=16, fill=rgba(color, 238))
    tw, th = text_size(d, label, fnt)
    d.text((x + (w - tw) / 2, y + (31 - th) / 2 - 1), label, font=fnt, fill=WHITE)


def bullet_list(
    img: Image.Image,
    x: int,
    y: int,
    items: Iterable[str],
    max_w: int,
    color: tuple[int, int, int] = BLUE2,
    fnt: ImageFont.FreeTypeFont | None = None,
    gap: int = 12,
) -> int:
    fnt = fnt or F["body"]
    d = ImageDraw.Draw(img, "RGBA")
    yy = y
    for item in items:
        d.ellipse((x, yy + 8, x + 9, yy + 17), fill=rgba(color))
        new_y = draw_wrapped(d, (x + 20, yy), item, fnt, max_w - 20, fill=SUBTLE, line_gap=7)
        yy = new_y + gap
    return yy


def arrow(img: Image.Image, start: tuple[int, int], end: tuple[int, int], color: tuple[int, int, int] = BLUE2, width: int = 4) -> None:
    d = ImageDraw.Draw(img, "RGBA")
    x1, y1 = start
    x2, y2 = end
    d.line((x1, y1, x2, y2), fill=rgba(color, 230), width=width)
    ang = math.atan2(y2 - y1, x2 - x1)
    size = 13
    pts = [
        (x2, y2),
        (x2 - size * math.cos(ang - math.pi / 6), y2 - size * math.sin(ang - math.pi / 6)),
        (x2 - size * math.cos(ang + math.pi / 6), y2 - size * math.sin(ang + math.pi / 6)),
    ]
    d.polygon(pts, fill=rgba(color, 230))


def add_header(img: Image.Image, slide_no: int, kicker: str, title: str, subtitle: str = "") -> ImageDraw.ImageDraw:
    d = ImageDraw.Draw(img, "RGBA")
    d.text((50, 40), kicker, font=F["kicker"], fill=(147, 197, 253))
    d.text((50, 74), title, font=F["title"], fill=WHITE)
    if subtitle:
        d.text((50, 121), subtitle, font=F["subtitle"], fill=SUBTLE)
    d.text((48, 684), "Coroutine Technology Research · 15-min presentation", font=F["small"], fill=MUTED)
    footer = f"{slide_no:02d}/18"
    tw, _ = text_size(d, footer, F["small"])
    d.text((1232 - tw, 684), footer, font=F["small"], fill=MUTED)
    return d


def title_in_card(img: Image.Image, x: int, y: int, kicker: str, title: str) -> None:
    d = ImageDraw.Draw(img, "RGBA")
    d.text((x, y), kicker, font=F["kicker"], fill=(147, 197, 253))
    d.text((x, y + 37), title, font=F["h2"], fill=WHITE)


def render_slide(slide_no: int, kicker: str, title: str, subtitle: str, body_fn) -> Image.Image:
    bg = gradient_background()
    img = bg.copy()
    add_header(img, slide_no, kicker, title, subtitle)
    body_fn(img)
    flattened = bg.copy()
    flattened.alpha_composite(img)
    return flattened.convert("RGB")


def slide01() -> Image.Image:
    def body(img: Image.Image) -> None:
        d = ImageDraw.Draw(img, "RGBA")
        card(img, (48, 164, 1184, 394), BLUE, fill_alpha=32, radius=30, accent_width=0)
        d.text((96, 225), "会用协程，不是记住一个语法", font=F["h1"], fill=WHITE)
        d.text((96, 294), "而是理解等待如何被重新调度", font=F["h1"], fill=WHITE)
        d.text((100, 363), "主线：问题动机 → 底层机制 → 语言路线 → 实验边界 → 工程判断", font=F["body2"], fill=TEXT)
        labels = [("线程瓶颈", RED), ("事件驱动", GREEN), ("协程抽象", BLUE), ("运行时调度", PURPLE), ("实验验证", SLATE)]
        x = 96
        for label, color in labels:
            pill(img, x, 442, 130, label, color, F["body_bold"])
            x += 156
    return render_slide(1, "PARALLEL PROGRAMMING · COROUTINE RESEARCH", "协程：把“等待”变便宜的并发抽象", "从线程瓶颈、运行时机制到本地 TCP I/O 实验验证", body)


def slide02() -> Image.Image:
    def body(img: Image.Image) -> None:
        d = ImageDraw.Draw(img, "RGBA")
        card(img, (48, 166, 724, 392), BLUE, fill_alpha=34)
        title_in_card(img, 82, 204, "REQUEST LIFECYCLE", "计算很短，等待很长")
        x0, y0 = 92, 327
        d.text((92, 294), "一次请求常见的耗时结构", font=F["body"], fill=SUBTLE)
        d.rounded_rectangle((x0, y0, x0 + 96, y0 + 42), radius=11, fill=rgba(BLUE, 255))
        d.text((x0 + 31, y0 + 10), "CPU", font=F["body_bold"], fill=WHITE)
        d.rounded_rectangle((x0 + 116, y0, x0 + 524, y0 + 42), radius=11, fill=(255, 255, 255, 30), outline=(255, 255, 255, 54))
        d.text((x0 + 235, y0 + 10), "等待 DB / RPC / 网络", font=F["body"], fill=SUBTLE)
        d.rounded_rectangle((x0 + 544, y0, x0 + 628, y0 + 42), radius=11, fill=rgba(BLUE, 255))
        d.text((x0 + 570, y0 + 10), "CPU", font=F["body_bold"], fill=WHITE)
        bullet_list(img, 92, 436, ["线程模型：等待期间仍占一个 OS 线程", "协程模型：挂起任务，线程继续执行其他可运行任务"], 610, BLUE2, F["body2"], gap=18)

        card(img, (792, 166, 440, 182), GREEN, fill_alpha=28)
        title_in_card(img, 824, 204, "WAIT SOURCES", "等待来自哪里")
        bullet_list(img, 824, 274, ["网络包到达", "数据库 / Redis / 消息队列", "RPC 下游响应", "定时器、连接池、限流器"], 360, GREEN2, F["body"], gap=6)
        card(img, (792, 368, 440, 190), RED, fill_alpha=28)
        title_in_card(img, 824, 406, "WHY IT MATTERS", "并发扩大后成本急剧放大")
        d.text((824, 462), "10K+", font=F["metric"], fill=WHITE)
        d.text((970, 454), "连接同时等待时", font=F["body"], fill=SUBTLE)
        d.text((970, 484), "线程栈、调度和切换都会放大", font=F["body"], fill=SUBTLE)
    return render_slide(2, "PROBLEM", "高并发服务为什么卡在等待", "大量请求处于网络、数据库、RPC 或定时器等待状态。", body)


def slide03() -> Image.Image:
    def body(img: Image.Image) -> None:
        d = ImageDraw.Draw(img, "RGBA")
        card(img, (48, 166, 1184, 126), BLUE, fill_alpha=34)
        d.text((82, 207), "协程不是凭空出现，而是事件驱动高吞吐与顺序代码可读性的折中", font=F["h2"], fill=WHITE)
        d.text((82, 249), "旧模型并未失效，关键是根据瓶颈选择抽象。", font=F["body"], fill=SUBTLE)
        items = [
            ("进程", "隔离强", "创建、切换、内存成本高", SLATE),
            ("线程", "代码直观", "高并发下线程仍昂贵", RED),
            ("事件循环", "少线程高吞吐", "回调复杂，状态分散", GREEN),
            ("协程", "顺序代码表达等待", "依赖运行时和非阻塞生态", BLUE),
            ("虚拟线程", "接近线程心智", "仍需关注 pinning 与下游容量", PURPLE),
        ]
        x = 48
        for name, main, detail, color in items:
            w = 216 if name != "虚拟线程" else 240
            card(img, (x, 326, w, 232), color, fill_alpha=28)
            d.text((x + 30, 371), name, font=F["h3"], fill=WHITE)
            d.text((x + 30, 414), main, font=F["body2"], fill=TEXT)
            draw_wrapped(d, (x + 30, 448), detail, F["small"], w - 58, fill=MUTED)
            if name != "虚拟线程":
                arrow(img, (x + w + 8, 442), (x + w + 30, 442), BLUE2, width=3)
            x += 236
    return render_slide(3, "EVOLUTION", "并发模型一步步降低等待成本", "从进程到线程，再到事件循环与协程，本质是在重新平衡隔离、可读性和资源效率。", body)


def slide04() -> Image.Image:
    def body(img: Image.Image) -> None:
        d = ImageDraw.Draw(img, "RGBA")
        cols = [
            (48, RED, "THREAD STYLE", "同步线程式代码", ["调用链直观", "等待也占线程", "高并发资源成本高"], ["data = read()", "return parse(data)"]),
            (460, GREEN, "EVENT LOOP", "事件循环回调", ["少线程高吞吐", "回调链复杂", "状态分散"], ["read(on_done)", "on_done -> parse()"]),
            (872, BLUE, "COROUTINE", "async / await 协程", ["等待不独占线程", "代码按流程阅读", "运行时恢复执行"], ["data = await read()", "return parse(data)"]),
        ]
        for x, color, k, t, bullets, code in cols:
            card(img, (x, 166, 360, 392), color, fill_alpha=34 if color == BLUE else 28)
            title_in_card(img, x + 30, 204, k, t)
            bullet_list(img, x + 30, 304, bullets, 300, color, F["body"], gap=12)
            d.rounded_rectangle((x + 30, 430, x + 330, 502), radius=15, fill=(255, 255, 255, 26), outline=(255, 255, 255, 44))
            d.text((x + 54, 451), code[0], font=F["code"], fill=(219, 234, 254))
            d.text((x + 54, 478), code[1], font=F["code"], fill=(219, 234, 254))
    return render_slide(4, "ABSTRACTION", "事件循环到协程：把性能重新包装成可读代码", "协程的价值不只是性能，也是在修复异步代码的可维护性。", body)


def slide05() -> Image.Image:
    def body(img: Image.Image) -> None:
        d = ImageDraw.Draw(img, "RGBA")
        card(img, (48, 166, 730, 392), BLUE, fill_alpha=34)
        title_in_card(img, 82, 204, "EXECUTION TRACK", "普通函数连续执行；协程在 await 点保存现场")
        d.text((92, 324), "普通函数", font=F["body2"], fill=TEXT)
        d.line((220, 334, 696, 334), fill=rgba(MUTED, 190), width=8)
        d.text((92, 420), "协程函数", font=F["body2"], fill=TEXT)
        d.line((220, 430, 360, 430), fill=rgba(BLUE2, 240), width=8)
        d.line((448, 430, 596, 430), fill=rgba(BLUE2, 240), width=8)
        d.line((660, 430, 696, 430), fill=rgba(BLUE2, 240), width=8)
        for cx, label in [(360, "await I/O"), (596, "resume")]:
            d.ellipse((cx - 13, 417, cx + 13, 443), fill=rgba(BLUE))
            tw, _ = text_size(d, label, F["small"])
            d.text((cx - tw / 2, 463), label, font=F["small"], fill=MUTED)
        card(img, (804, 166, 428, 178), GREEN, fill_alpha=28)
        title_in_card(img, 834, 204, "STATE SAVED", "挂起时保存什么")
        bullet_list(img, 834, 268, ["局部变量", "下一步执行位置", "返回值与异常", "恢复句柄 / continuation"], 350, GREEN2, F["body"], gap=4)
        card(img, (804, 364, 428, 194), RED, fill_alpha=28)
        title_in_card(img, 834, 402, "BOUNDARY", "协程不是自动并行")
        draw_wrapped(d, (834, 462), "它让等待更便宜，但不会突破 CPU 核心限制。", F["body2"], 350, fill=TEXT)
    return render_slide(5, "DEFINITION", "协程是可暂停、可恢复的函数", "核心不是并行，而是执行过程可以在挂起点被切开。", body)


def slide06() -> Image.Image:
    def body(img: Image.Image) -> None:
        card(img, (48, 166, 560, 392), BLUE, fill_alpha=34)
        title_in_card(img, 82, 204, "STACKLESS", "编译器拆成状态机")
        bullet_list(img, 82, 304, ["不保存完整调用栈", "局部变量进入协程帧", "await 沿调用链显式传播", "代表：C++20、Python、C#"], 460, BLUE2, F["body2"], gap=14)
        card(img, (648, 166, 584, 392), PURPLE, fill_alpha=30)
        title_in_card(img, 682, 204, "STACKFUL / FIBER-LIKE", "每个轻量执行单元保留自己的栈语义")
        bullet_list(img, 682, 304, ["更接近线程式心智", "调用链侵入性较低", "栈管理和调度更复杂", "代表：部分 fiber 库、虚拟线程内部思路"], 480, (196, 181, 253), F["body2"], gap=14)
    return render_slide(6, "IMPLEMENTATION TYPES", "Stackless 与 Stackful：两种协程实现心智", "实现方式决定了语言的侵入性、运行时复杂度和调试体验。", body)


def slide07() -> Image.Image:
    def body(img: Image.Image) -> None:
        d = ImageDraw.Draw(img, "RGBA")
        card(img, (48, 166, 1184, 392), BLUE, fill_alpha=34)
        d.text((82, 207), "COROUTINE LOWERING", font=F["kicker"], fill=(147, 197, 253))

        # Left: source coroutine.
        d.rounded_rectangle((82, 238, 386, 432), radius=18, fill=(15, 23, 42, 216), outline=(255, 255, 255, 42))
        d.text((106, 262), "async def fetch():", font=F["code"], fill=(191, 219, 254))
        d.text((126, 296), "conn = await open()", font=F["code"], fill=(226, 232, 240))
        d.text((126, 330), "data = await read(conn)", font=F["code"], fill=(226, 232, 240))
        d.text((126, 364), "return parse(data)", font=F["code"], fill=(226, 232, 240))
        d.text((106, 406), "源码中的 await 是控制权转移点", font=F["small"], fill=MUTED)

        arrow(img, (408, 334), (480, 334), BLUE2, width=5)
        d.text((415, 294), "编译/解释器", font=F["small"], fill=MUTED)
        d.text((421, 315), "降低为帧", font=F["small"], fill=MUTED)

        # Center: coroutine frame.
        d.rounded_rectangle((500, 220, 790, 478), radius=22, fill=(37, 99, 235, 54), outline=(96, 165, 250, 120), width=2)
        d.text((548, 248), "COROUTINE FRAME", font=F["h3"], fill=WHITE)
        frame_rows = [
            ("locals", "conn / data / 临时变量", BLUE2),
            ("state", "suspended_at = read()", GREEN2),
            ("exception", "返回值或异常槽", RED2),
            ("continuation", "下一次 resume 入口", (196, 181, 253)),
        ]
        yy = 286
        for name, desc, color in frame_rows:
            d.rounded_rectangle((530, yy, 760, yy + 39), radius=12, fill=(15, 23, 42, 180), outline=rgba(color, 120))
            d.text((548, yy + 9), name, font=F["code_small"], fill=color)
            d.text((650, yy + 9), desc, font=F["small"], fill=SUBTLE)
            yy += 48

        arrow(img, (804, 334), (878, 334), BLUE2, width=5)
        d.text((814, 294), "await 对象", font=F["small"], fill=MUTED)
        d.text((818, 315), "注册回调", font=F["small"], fill=MUTED)

        # Right: runtime chain.
        chain = [
            (900, 214, "awaiter", "挂到 I/O 或 Future", GREEN),
            (900, 292, "ready queue", "事件完成后入队", BLUE),
            (900, 370, "event loop", "取出可运行任务", PURPLE),
            (900, 448, "resume", "按 continuation 恢复", AMBER),
        ]
        for i, (x, y, head, desc, color) in enumerate(chain):
            d.rounded_rectangle((x, y, x + 276, y + 54), radius=16, fill=(255, 255, 255, 28), outline=rgba(color, 116))
            d.text((x + 22, y + 11), head, font=F["body_bold"], fill=WHITE)
            d.text((x + 128, y + 13), desc, font=F["small"], fill=SUBTLE)
            if i < len(chain) - 1:
                arrow(img, (x + 138, y + 60), (x + 138, y + 74), color, width=4)
        arrow(img, (900, 474), (790, 452), AMBER, width=4)

        d.rounded_rectangle((82, 512, 1176, 548), radius=16, fill=rgba(GREEN, 56), outline=rgba(GREEN2, 90))
        statement = "await = 保存现场 + 让出线程 + 事件完成后恢复执行"
        tw, th = text_size(d, statement, F["body2"])
        d.text((82 + (1094 - tw) / 2, 519), statement, font=F["body2"], fill=(209, 250, 229))
    return render_slide(7, "STATE MACHINE", "协程底层是状态保存、排队与恢复", "await 不是简单等待，而是一次由编译器和运行时共同完成的控制权转移。", body)


def slide08() -> Image.Image:
    def body(img: Image.Image) -> None:
        d = ImageDraw.Draw(img, "RGBA")
        card(img, (48, 166, 1184, 120), BLUE, fill_alpha=34)
        d.text((82, 207), "协程性能来自协同：编译器改写控制流，运行时调度任务，OS 提供非阻塞 I/O 通知", font=F["h2"], fill=WHITE)
        cols = [
            (48, 326, 360, "编译器 / 解释器", ["识别 await 点", "生成状态机或协程帧", "保存局部变量和恢复位置"], BLUE),
            (460, 326, 360, "运行时 / Scheduler", ["维护任务队列", "注册 I/O 事件", "恢复已就绪协程"], GREEN),
            (872, 326, 360, "操作系统", ["epoll/kqueue/IOCP", "socket readiness", "少量内核线程承载大量连接"], PURPLE),
        ]
        for x, y, w, title, bullets, color in cols:
            card(img, (x, y, w, 232), color, fill_alpha=28)
            d.text((x + 30, y + 44), title, font=F["h2"], fill=WHITE)
            bullet_list(img, x + 30, y + 96, bullets, w - 62, color, F["body"], gap=9)
    return render_slide(8, "RUNTIME", "编译器、运行时、OS 协同完成协程调度", "协程不是语言关键字单独完成的能力。", body)


def slide09() -> Image.Image:
    def body(img: Image.Image) -> None:
        d = ImageDraw.Draw(img, "RGBA")
        card(img, (48, 166, 1184, 392), BLUE, fill_alpha=30)
        rows = [
            ("Python", "asyncio / async-await", "显式事件循环，I/O 协作强，CPU 受 GIL 与单线程调度限制", BLUE),
            ("Go", "goroutine + channel", "语言级轻量任务，运行时 M:N 调度，工程默认并发工具", GREEN),
            ("C++20", "coroutine primitive", "只给底层机制，不内置调度器，生态与库设计决定可用性", PURPLE),
            ("C#", "Task / async-await", "成熟状态机模型，与 .NET 任务调度深度整合", AMBER),
            ("Java", "Virtual Threads", "以线程心智承载高并发阻塞式代码，需关注 pinning", RED),
        ]
        y = 202
        for lang, model, desc, color in rows:
            d.rounded_rectangle((82, y, 1176, y + 56), radius=15, fill=(255, 255, 255, 25), outline=rgba(color, 110))
            d.text((108, y + 14), lang, font=F["h3"], fill=WHITE)
            d.text((238, y + 15), model, font=F["body_bold"], fill=color)
            d.text((468, y + 15), desc, font=F["body"], fill=SUBTLE)
            y += 66
    return render_slide(9, "LANGUAGE MAP", "主流语言路线：同名“协程”，工程含义不同", "选型不能只看语法，而要看调度器、标准库、生态和阻塞代码兼容性。", body)


def slide10() -> Image.Image:
    def body(img: Image.Image) -> None:
        d = ImageDraw.Draw(img, "RGBA")
        cols = [
            (48, "C++20", "底层原语", ["不自带事件循环", "promise_type / awaiter 可定制", "适合库作者与高性能框架"], PURPLE),
            (460, "Go", "默认并发模型", ["goroutine 创建成本低", "M:N 调度隐藏复杂度", "channel 组织并发通信"], GREEN),
            (872, "Python", "显式异步生态", ["asyncio 适合 I/O 密集", "需要 awaitable 库链路", "CPU-bound 需进程池或原生扩展"], BLUE),
        ]
        for x, lang, tag, bullets, color in cols:
            card(img, (x, 166, 360, 392), color, fill_alpha=30)
            d.text((x + 30, 213), lang, font=F["metric2"], fill=WHITE)
            pill(img, x + 30, 266, 138, tag, color, F["body_bold"])
            bullet_list(img, x + 30, 324, bullets, 292, color, F["body2"], gap=16)
    return render_slide(10, "COMPARISON", "C++ / Go / Python：抽象层次差异巨大", "C++偏机制，Go偏运行时默认，Python偏显式事件循环。", body)


def slide11() -> Image.Image:
    def body(img: Image.Image) -> None:
        d = ImageDraw.Draw(img, "RGBA")
        card(img, (48, 166, 560, 392), AMBER, fill_alpha=30)
        d.text((82, 212), "C# async / await", font=F["metric2"], fill=WHITE)
        bullet_list(img, 82, 292, ["编译为状态机，返回 Task/ValueTask", "与 .NET 线程池、I/O 完成端口整合", "成熟生态，但仍需避免同步阻塞和上下文捕获误用"], 460, AMBER, F["body2"], gap=15)
        card(img, (648, 166, 584, 392), RED, fill_alpha=28)
        d.text((682, 212), "Java Virtual Threads", font=F["metric2"], fill=WHITE)
        bullet_list(img, 682, 292, ["目标是保留线程式代码心智", "阻塞点可卸载载体线程，适合服务端请求模型", "synchronized pinning、下游容量和连接池仍需治理"], 480, RED2, F["body2"], gap=15)
    return render_slide(11, "MODERN JVM/.NET", "C# 与 Java：从 async 状态机到虚拟线程", "现代平台正在把“高并发”重新包装进更接近业务代码的抽象。", body)


def slide12() -> Image.Image:
    def body(img: Image.Image) -> None:
        d = ImageDraw.Draw(img, "RGBA")
        card(img, (48, 166, 716, 392), BLUE, fill_alpha=34)
        title_in_card(img, 82, 204, "LOCAL TCP I/O", "主实验：本地真实 socket 往返")
        bullet_list(img, 82, 284, ["127.0.0.1 loopback TCP server，动态端口", "每个请求：连接 / 发送 / server 等待 20ms / 读取 OK", "asyncio.open_connection 并发协程 vs ThreadPoolExecutor + blocking socket", "任务数：100、500、1000、3000、5000；重复 5 次取中位数"], 620, BLUE2, F["body"], gap=10)
        card(img, (796, 166, 436, 188), GREEN, fill_alpha=28)
        title_in_card(img, 828, 204, "CPU BOUND", "边界实验：纯计算任务")
        bullet_list(img, 828, 284, ["任务数：50、100、200", "证明协程不创造 CPU 算力"], 350, GREEN2, F["body"], gap=9)
        card(img, (796, 374, 436, 184), PURPLE, fill_alpha=28)
        title_in_card(img, 828, 412, "CONTROL", "旧 sleep 实验降级")
        draw_wrapped(d, (828, 472), "sleep 只能说明调度语义，不能作为真实 I/O 的主证据。", F["body2"], 350, fill=TEXT)
    return render_slide(12, "EXPERIMENT DESIGN", "实验设计：本地真实 I/O + CPU 边界", "主证据来自真实 TCP socket，避免只用 sleep 模拟等待。", body)


def slide13() -> Image.Image:
    def body(img: Image.Image) -> None:
        d = ImageDraw.Draw(img, "RGBA")
        cards = [
            (48, 166, 560, 170, "耗时 / 吞吐", "中位耗时作为主读数；吞吐=完成任务数/耗时。", BLUE),
            (648, 166, 584, 170, "业务新增线程峰值", "采样线程数并扣除 server 基线和采样线程，避免污染。", GREEN),
            (48, 368, 560, 190, "RSS 内存增量", "使用 psutil 采样进程常驻内存变化，反映系统级内存趋势。", PURPLE),
            (648, 368, 584, 190, "tracemalloc 定位", "只作为 Python 分配补充，不误读为进程总内存。", AMBER),
        ]
        for x, y, w, h, title, desc, color in cards:
            card(img, (x, y, w, h), color, fill_alpha=30)
            d.text((x + 34, y + 48), title, font=F["h2"], fill=WHITE)
            draw_wrapped(d, (x + 34, y + 94), desc, F["body2"], w - 76, fill=TEXT)
    return render_slide(13, "METRICS", "实验指标解释：看耗时，也看资源代价", "线程、RSS、吞吐三类指标共同解释“等待成本”。", body)


def slide14() -> Image.Image:
    a = metric("tcp_io", 5000, "asyncio")
    t = metric("tcp_io", 5000, "threads-200")

    def body(img: Image.Image) -> None:
        d = ImageDraw.Draw(img, "RGBA")
        chart_card(img, (48, 166, 910, 430), ASSETS / "exp_io_thread_bar.png", pad=16)
        card(img, (986, 166, 246, 430), BLUE, fill_alpha=30)
        d.text((1018, 210), "KEY TAKEAWAY", font=F["kicker"], fill=(147, 197, 253))
        d.text((1018, 256), f"{int(a.threads)} vs {int(t.threads)}", font=F["metric"], fill=WHITE)
        draw_wrapped(d, (1018, 310), "5000 个真实 TCP I/O 请求下，asyncio 几乎不增加业务线程。", F["body2"], 184, fill=TEXT)
        d.line((1018, 394, 1200, 394), fill=(255, 255, 255, 60), width=1)
        d.text((1018, 428), f"asyncio 中位耗时 {a.duration:.2f}s", font=F["small"], fill=SUBTLE)
        d.text((1018, 456), f"threads-200 中位耗时 {t.duration:.2f}s", font=F["small"], fill=SUBTLE)
        draw_wrapped(d, (1018, 502), "核心结论不是“永远更快”，而是“等待并发更省线程”。", F["small"], 176, fill=MUTED, line_gap=6)
    return render_slide(14, "I/O RESULT", "I/O结果：asyncio用更少业务线程承载同等并发", "主图使用线程峰值对比，图表占页面主体，避免信息被压缩。", body)


def slide15() -> Image.Image:
    a = metric("tcp_io", 5000, "asyncio")
    t = metric("tcp_io", 5000, "threads-200")
    ratio = t.threads / max(a.threads, 1)

    def body(img: Image.Image) -> None:
        d = ImageDraw.Draw(img, "RGBA")
        chart_card(img, (48, 166, 875, 430), ASSETS / "exp_io_scaling_async_vs_thread200.png", pad=14)
        card(img, (952, 166, 280, 198), GREEN, fill_alpha=30)
        d.text((984, 208), "SCALING", font=F["kicker"], fill=(167, 243, 208))
        d.text((984, 254), f"{a.throughput:.0f}", font=F["metric"], fill=WHITE)
        d.text((984, 310), "tasks/s · asyncio @5000", font=F["body"], fill=SUBTLE)
        card(img, (952, 386, 280, 210), PURPLE, fill_alpha=30)
        d.text((984, 428), "RESOURCE RATIO", font=F["kicker"], fill=(196, 181, 253))
        d.text((984, 474), f"{ratio:.0f}×", font=F["metric"], fill=WHITE)
        draw_wrapped(d, (984, 528), "线程池换吞吐的同时增加业务线程峰值；协程更适合大量等待任务。", F["body"], 212, fill=TEXT)
    return render_slide(15, "I/O SCALING", "I/O扩展性：吞吐提升不能只看耗时，还要看线程代价", "同样是完成请求，资源曲线决定服务容量上限。", body)


def slide16() -> Image.Image:
    a = metric("cpu_bound", 200, "asyncio")
    t = metric("cpu_bound", 200, "threads-200")
    normalized = t.duration / max(a.duration, 0.001)

    def body(img: Image.Image) -> None:
        d = ImageDraw.Draw(img, "RGBA")
        chart_card(img, (48, 166, 900, 430), ASSETS / "exp_cpu_normalized_duration.png", pad=16)
        card(img, (976, 166, 256, 430), RED, fill_alpha=30)
        d.text((1008, 210), "CPU BOUNDARY", font=F["kicker"], fill=(252, 165, 165))
        d.text((1008, 256), f"{normalized:.2f}×", font=F["metric"], fill=WHITE)
        draw_wrapped(d, (1008, 310), "threads-200 相对 asyncio 的 200 任务归一化耗时接近 1。", F["body2"], 190, fill=TEXT)
        d.line((1008, 410, 1200, 410), fill=(255, 255, 255, 60), width=1)
        bullet_list(img, 1008, 440, ["协程让等待便宜", "不增加 CPU 核心", "CPU 密集应考虑进程池、向量化或原生扩展"], 190, RED2, F["small"], gap=8)
    return render_slide(16, "CPU RESULT", "CPU结果：协程不是CPU加速工具", "CPU-bound 场景下，耗时接近才是正确结论。", body)


def slide17() -> Image.Image:
    def body(img: Image.Image) -> None:
        d = ImageDraw.Draw(img, "RGBA")
        card(img, (48, 166, 560, 392), BLUE, fill_alpha=34)
        title_in_card(img, 82, 204, "USE WHEN", "适合使用协程")
        bullet_list(img, 82, 292, ["高并发网络 I/O", "请求中存在大量等待", "依赖库提供非阻塞接口", "需要用顺序代码表达异步流程"], 470, BLUE2, F["body2"], gap=15)
        card(img, (648, 166, 584, 392), RED, fill_alpha=28)
        title_in_card(img, 682, 204, "WATCH OUT", "常见工程坑")
        bullet_list(img, 682, 292, ["在事件循环中调用阻塞函数", "无限制 fan-out 打爆下游服务", "错误处理和取消传播缺失", "把 CPU-bound 误当协程优化对象"], 490, RED2, F["body2"], gap=15)
    return render_slide(17, "ENGINEERING", "工程选型：协程解决等待，不替代容量治理", "真正落地时，限流、超时、取消、连接池和可观测性同样重要。", body)


def slide18() -> Image.Image:
    def body(img: Image.Image) -> None:
        d = ImageDraw.Draw(img, "RGBA")
        card(img, (48, 166, 724, 392), BLUE, fill_alpha=34)
        d.text((82, 214), "总结", font=F["metric2"], fill=WHITE)
        bullet_list(img, 82, 292, ["协程把等待从线程占用中解耦出来", "底层依赖状态保存、事件队列和恢复链", "不同语言的协程能力差异来自运行时与生态", "本地 TCP 实验证明：I/O 等待场景下协程显著降低业务线程峰值"], 610, BLUE2, F["body2"], gap=14)
        card(img, (804, 166, 428, 184), GREEN, fill_alpha=28)
        d.text((836, 210), "PDF 补充文档", font=F["h2"], fill=WHITE)
        draw_wrapped(d, (836, 266), "可配合提交《协程技术调研报告.pdf》，展示完整调研、实验方法、数据解释、局限与参考资料。", F["body"], 348, fill=TEXT)
        card(img, (804, 374, 428, 184), PURPLE, fill_alpha=28)
        d.text((836, 418), "AI 使用说明", font=F["h2"], fill=WHITE)
        draw_wrapped(d, (836, 474), "AI 用于资料整理、结构设计、实验脚本与可视化草拟；关键结论由实验数据和资料来源校验。", F["body"], 348, fill=TEXT)
    return render_slide(18, "CLOSING", "总结与AI使用说明", "15分钟主讲到此结束，完整材料见 PDF 文档。", body)


SLIDE_BUILDERS = [
    slide01,
    slide02,
    slide03,
    slide04,
    slide05,
    slide06,
    slide07,
    slide08,
    slide09,
    slide10,
    slide11,
    slide12,
    slide13,
    slide14,
    slide15,
    slide16,
    slide17,
    slide18,
]


def main() -> None:
    OUT.mkdir(exist_ok=True)
    for stale in OUT.glob("slide_*.png"):
        stale.unlink()
    for idx, build in enumerate(SLIDE_BUILDERS, start=1):
        img = build()
        path = OUT / f"slide_{idx:02d}.png"
        img.save(path, "PNG", optimize=True)

    # Keep a static HTML contact sheet for quick local inspection without touching the SVG source preview.
    html = [
        "<!doctype html><meta charset='utf-8'><title>PPTX slide PNG preview</title>",
        "<style>body{margin:0;background:#111827;color:#e5e7eb;font-family:Segoe UI,Microsoft YaHei,sans-serif}"
        ".grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:18px;padding:18px}"
        "figure{margin:0;background:#020617;border:1px solid #334155;border-radius:10px;padding:10px}"
        "img{width:100%;display:block;border-radius:6px}figcaption{font-size:12px;margin-top:8px;color:#94a3b8}</style><div class='grid'>",
    ]
    for idx in range(1, 19):
        html.append(f"<figure><img src='slide_{idx:02d}.png'><figcaption>slide_{idx:02d}.png</figcaption></figure>")
    html.append("</div>")
    (OUT / "index.html").write_text("\n".join(html), encoding="utf-8")

    # Copy the most relevant chart PNGs into the folder so PPTX media can be audited quickly.
    for name in [
        "exp_io_thread_bar.png",
        "exp_io_scaling_async_vs_thread200.png",
        "exp_cpu_normalized_duration.png",
    ]:
        src = ASSETS / name
        if src.exists():
            shutil.copy2(src, OUT / name)


if __name__ == "__main__":
    main()
