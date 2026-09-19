#!/usr/bin/env python3
"""optimize_images.py — _research/masters/**/*.png (gitignored, full-size) → Lectures/assets/img/**/*.webp.

The deck ships the WebP files; the masters stay on the author's machine. Re-run after
generating or regenerating any plate:  python3 scripts/optimize_images.py
"""
import pathlib
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC, DST = ROOT / "_research" / "masters", ROOT / "Lectures" / "assets" / "img"
WIDTH, QUALITY = 1600, 82

for src in sorted(SRC.rglob("*.png")):
    dst = (DST / src.relative_to(SRC)).with_suffix(".webp")
    dst.parent.mkdir(parents=True, exist_ok=True)
    im = Image.open(src).convert("RGB")
    if im.width > WIDTH:
        im = im.resize((WIDTH, round(im.height * WIDTH / im.width)), Image.LANCZOS)
    im.save(dst, "WEBP", quality=QUALITY, method=6)
    print(f"{dst.relative_to(ROOT)}  {dst.stat().st_size // 1024} KB")
