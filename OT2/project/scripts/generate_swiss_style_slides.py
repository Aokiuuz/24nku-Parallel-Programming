from __future__ import annotations

import re
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent


def find_project_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "final").exists():
            return candidate
    return start


ROOT = find_project_root(SCRIPT_DIR)
SRC = ROOT / "final" / "svg_slides"
OUT = ROOT / "final" / "svg_slides_swiss"
OUT.mkdir(parents=True, exist_ok=True)

IKB = "#002FA7"
PAPER = "#FAFAF8"
INK = "#0A0A0A"
GREY_1 = "#F0F0EE"
GREY_2 = "#D4D4D2"
GREY_3 = "#737373"


SWISS_STYLE = f"""<style>
      .page {{ font-family: "Inter", "Helvetica Neue", "Helvetica", "Noto Sans SC", "Microsoft YaHei", "Microsoft YaHei UI", "DengXian", "SimSun", "NSimSun", Arial, sans-serif; }}
      .card {{ fill: rgba(255,255,255,0.78); stroke: {GREY_2}; stroke-width: 1.15; }}
      .card2 {{ fill: rgba(255,255,255,0.88); stroke: {INK}; stroke-width: 1.15; }}
      .chartcard {{ fill: #FFFFFF; stroke: {INK}; stroke-width: 1.15; }}
      .kicker {{ fill: {IKB}; font-size: 14.5px; font-weight: 700; letter-spacing: 1.9px; }}
      .title {{ fill: {INK}; font-size: 39px; font-weight: 560; letter-spacing: 0; }}
      .h1 {{ fill: {INK}; font-size: 52px; font-weight: 360; letter-spacing: 0; }}
      .h2 {{ fill: {INK}; font-size: 24px; font-weight: 560; letter-spacing: 0; }}
      .h3 {{ fill: {INK}; font-size: 19.5px; font-weight: 620; letter-spacing: 0; }}
      .body {{ fill: #242424; font-size: 16.8px; font-weight: 470; letter-spacing: 0; }}
      .body2 {{ fill: {INK}; font-size: 19.2px; font-weight: 560; letter-spacing: 0; }}
      .small {{ fill: {GREY_3}; font-size: 13.5px; font-weight: 520; letter-spacing: 0; }}
      .metric {{ fill: {IKB}; font-size: 44px; font-weight: 520; letter-spacing: 0; }}
      .axis {{ stroke: {GREY_2}; stroke-width: 1; }}
      .node {{ fill: rgba(255,255,255,0.82); stroke: {GREY_2}; stroke-width: 1.1; }}
      .line {{ fill: none; stroke-width: 3; stroke-linecap: square; stroke-linejoin: miter; }}
    </style>"""


def swiss_grid() -> str:
    vertical = "\n".join(
        f'  <line x1="{x}" y1="0" x2="{x}" y2="720" stroke="{GREY_2}" stroke-width="0.65" opacity="0.35"/>'
        for x in range(80, 1280, 70)
    )
    horizontal = "\n".join(
        f'  <line x1="0" y1="{y}" x2="1280" y2="{y}" stroke="{GREY_2}" stroke-width="0.65" opacity="0.22"/>'
        for y in range(80, 720, 70)
    )
    dots = []
    for x in range(72, 1280, 56):
        for y in range(64, 720, 56):
            if (x + y) % 168 == 0:
                dots.append(f'  <circle cx="{x}" cy="{y}" r="1.5" fill="{IKB}" opacity="0.26"/>')
    return (
        f'  <rect class="page" width="1280" height="720" fill="{PAPER}"/>\n'
        f'  <g class="swiss-grid">\n{vertical}\n{horizontal}\n' + "\n".join(dots) + "\n  </g>"
    )


def transform_svg(svg: str) -> str:
    svg = re.sub(r"<style>.*?</style>", SWISS_STYLE, svg, flags=re.S)
    svg = svg.replace('  <rect class="page" width="1280" height="720" fill="url(#bg)"/>', swiss_grid())
    svg = re.sub(r'\n  <circle cx="1126" cy="-88" r="282" fill="#2563EB" opacity="0\.12"/>', "", svg)
    svg = re.sub(r'\n  <circle cx="-86" cy="650" r="310" fill="#059669" opacity="0\.10"/>', "", svg)

    replacements = {
        "#2563EB": IKB,
        "#60A5FA": IKB,
        "#93C5FD": IKB,
        "#059669": IKB,
        "#34D399": IKB,
        "#DC2626": IKB,
        "#F87171": IKB,
        "#7C3AED": IKB,
        "#C4B5FD": IKB,
        "#64748B": GREY_3,
        "#94A3B8": GREY_3,
        "#CBD5E1": "#242424",
        "#E2E8F0": INK,
        "#E5E7EB": INK,
        "#F8FAFC": INK,
        "#111827": INK,
    }
    for old, new in replacements.items():
        svg = svg.replace(old, new)

    rgba_replacements = {
        "rgba(37,99,235,0.20)": "rgba(0,47,167,0.10)",
        "rgba(37,99,235,0.22)": "rgba(0,47,167,0.10)",
        "rgba(37,99,235,0.24)": "rgba(0,47,167,0.12)",
        "rgba(5,150,105,0.18)": "rgba(0,47,167,0.08)",
        "rgba(5,150,105,0.20)": "rgba(0,47,167,0.08)",
        "rgba(5,150,105,0.22)": "rgba(0,47,167,0.08)",
        "rgba(5,150,105,0.23)": "rgba(0,47,167,0.08)",
        "rgba(5,150,105,0.25)": "rgba(0,47,167,0.10)",
        "rgba(220,38,38,0.17)": "rgba(0,47,167,0.08)",
        "rgba(220,38,38,0.20)": "rgba(0,47,167,0.08)",
        "rgba(124,58,237,0.18)": "rgba(0,47,167,0.08)",
        "rgba(255,255,255,0.08)": "rgba(255,255,255,0.72)",
        "rgba(255,255,255,0.078)": "rgba(255,255,255,0.78)",
        "rgba(255,255,255,0.112)": "rgba(255,255,255,0.88)",
        "rgba(15,23,42,0.82)": "rgba(255,255,255,0.94)",
        "rgba(15,23,42,0.75)": "rgba(255,255,255,0.86)",
        "rgba(15,23,42,0.72)": "rgba(255,255,255,0.94)",
    }
    for old, new in rgba_replacements.items():
        svg = svg.replace(old, new)

    svg = re.sub(r'stroke="rgba\((96,165,250|52,211,153|248,113,113|196,181,253),0\.(32|34|35|36|40|42)\)"', f'stroke="{IKB}"', svg)
    svg = svg.replace('fill="#FFFFFF"', f'fill="{IKB}"')
    svg = svg.replace('fill="#fff"', f'fill="{IKB}"')

    # Keep text inside strong accent pills readable.
    svg = re.sub(
        rf'(<rect[^>]+fill="{IKB}"[^>]*/><text[^>]+fill=)"{IKB}"',
        r'\1"#FFFFFF"',
        svg,
    )
    svg = re.sub(r'rx="30"', 'rx="0"', svg)
    svg = re.sub(r'rx="22"', 'rx="0"', svg)
    svg = re.sub(r'rx="20"', 'rx="0"', svg)
    svg = re.sub(r'rx="18"', 'rx="0"', svg)
    return svg


def main() -> None:
    for stale in OUT.glob("slide_*.svg"):
        stale.unlink()

    slide_files = sorted(SRC.glob("slide_*.svg"))
    if len(slide_files) != 20:
        raise SystemExit(f"Expected 20 source SVG slides, found {len(slide_files)} in {SRC}")

    for src in slide_files:
        transformed = transform_svg(src.read_text(encoding="utf-8"))
        (OUT / src.name).write_text(transformed, encoding="utf-8")

    html = [
        '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>协程技术调研 · Swiss SVG Slides</title>',
        '<style>body{margin:0;background:#fafaf8;color:#0a0a0a;font-family:Inter,Helvetica,"Noto Sans SC","Microsoft YaHei",sans-serif}main{max-width:1320px;margin:0 auto;padding:28px}section{margin:0 0 36px}h1{font-size:28px;font-weight:560}h2{font-size:16px;color:#737373}img{width:100%;border:1px solid #d4d4d2;background:#fafaf8}</style>',
        '</head><body><main><h1>协程技术调研 · 瑞士风格 SVG Slides</h1>',
    ]
    for index in range(1, len(slide_files) + 1):
        name = f"slide_{index:02d}.svg"
        html.append(f'<section><h2>{name}</h2><img src="{name}" alt="{name}"></section>')
    html.append("</main></body></html>")
    (OUT / "index.html").write_text("\n".join(html), encoding="utf-8")
    print(f"Generated {len(slide_files)} Swiss SVG slides in {OUT}")


if __name__ == "__main__":
    main()
