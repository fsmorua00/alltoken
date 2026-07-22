#!/usr/bin/env python3
"""
tokenwise text-to-image (EXPERIMENTAL / opt-in) — render a text file as a PNG.

The idea (from the "images instead of text" trick): a page of text attached as an
image can sometimes be processed with fewer tokens than the same text inline.

Honest caveats — read before using:
  * It is LOSSY. Claude reads the image via OCR-like vision; it can misread
    characters, whitespace, and code. NEVER use this for code, configs, commands,
    or anything that must be exact.
  * Savings are NOT guaranteed. Image tokens scale with resolution/detail; a dense
    or high-res image can cost MORE than the text. Measure before trusting it.
  * Best case: long, low-stakes prose you want summarized, not reproduced verbatim.

Requires Pillow (`pip install Pillow`). Exits cleanly with instructions if missing.

Usage:
    python text_to_image.py input.txt -o out.png [--width 1000] [--font-size 18]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="render text file to PNG (experimental)")
    ap.add_argument("input", help="path to a UTF-8 text file")
    ap.add_argument("-o", "--output", default=None, help="output PNG path")
    ap.add_argument("--width", type=int, default=1000, help="image width in px")
    ap.add_argument("--font-size", type=int, default=18, help="font size in px")
    ap.add_argument("--padding", type=int, default=20, help="padding in px")
    args = ap.parse_args(argv)

    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print(
            "text_to_image requires Pillow. Install it with:\n"
            "    pip install Pillow\n"
            "Then re-run. (This feature is experimental and lossy — see the module "
            "docstring before relying on it.)",
            file=sys.stderr,
        )
        return 3

    src = Path(args.input)
    if not src.is_file():
        print(f"error: {src} not found", file=sys.stderr)
        return 2
    text = src.read_text(encoding="utf-8", errors="replace")
    out = Path(args.output) if args.output else src.with_suffix(".png")

    try:
        font = ImageFont.truetype("DejaVuSansMono.ttf", args.font_size)
    except OSError:
        font = ImageFont.load_default()

    # Wrap text to the image width using character-cell estimation.
    tmp = Image.new("RGB", (10, 10))
    draw = ImageDraw.Draw(tmp)
    char_w = max(1, draw.textlength("M", font=font))
    max_chars = max(10, int((args.width - 2 * args.padding) / char_w))

    lines: list[str] = []
    for raw in text.splitlines() or [""]:
        if not raw:
            lines.append("")
            continue
        while len(raw) > max_chars:
            lines.append(raw[:max_chars])
            raw = raw[max_chars:]
        lines.append(raw)

    line_h = args.font_size + 6
    height = args.padding * 2 + line_h * max(1, len(lines))
    img = Image.new("RGB", (args.width, height), "white")
    d = ImageDraw.Draw(img)
    y = args.padding
    for ln in lines:
        d.text((args.padding, y), ln, fill="black", font=font)
        y += line_h

    img.save(out)
    print(f"wrote {out} ({args.width}x{height}px, {len(lines)} lines)")
    print("Reminder: lossy. Do not use for code/configs/commands.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
