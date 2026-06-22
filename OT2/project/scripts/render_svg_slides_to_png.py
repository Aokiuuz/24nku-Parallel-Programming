from __future__ import annotations

import os
from pathlib import Path

from playwright.sync_api import sync_playwright


SCRIPT_DIR = Path(__file__).resolve().parent


def find_project_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "final").exists():
            return candidate
    return start


ROOT = find_project_root(SCRIPT_DIR)
SLIDES_DIR = ROOT / os.environ.get("SLIDES_DIR", "final/svg_slides")
OUT_DIR = ROOT / os.environ.get("PNG_OUT_DIR", "project/build/rendered_png_slides")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def main() -> None:
    slide_files = sorted(SLIDES_DIR.glob("slide_*.svg"))
    expected = int(os.environ.get("EXPECTED_SLIDES", str(len(slide_files))))
    if len(slide_files) != expected:
        raise SystemExit(f"Expected {expected} SVG slides, found {len(slide_files)} in {SLIDES_DIR}")

    for stale in OUT_DIR.glob("slide_*.png"):
        stale.unlink()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=2)
        for index, svg_path in enumerate(slide_files, start=1):
            svg = svg_path.read_text(encoding="utf-8")
            page.set_content(
                "<!doctype html><html><head><meta charset='utf-8'>"
                "<style>html,body{margin:0;width:1280px;height:720px;overflow:hidden;background:transparent}"
                "svg{display:block;width:1280px;height:720px}</style></head><body>"
                f"{svg}</body></html>",
                wait_until="load",
            )
            page.screenshot(path=str(OUT_DIR / f"slide_{index:02d}.png"), full_page=False)
        browser.close()
    print(f"Rendered {len(slide_files)} PNG slides to {OUT_DIR}")


if __name__ == "__main__":
    main()
