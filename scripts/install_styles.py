#!/usr/bin/env python3
"""
tokenwise install-styles — copy the bundled output styles into a project (or the
user home) so they can be activated with Claude Code's `/output-style` command.

Output styles change how Claude writes its responses, which is the cheapest lever
on OUTPUT tokens. This just places the .md files where Claude Code looks for them:
  * project scope:  <target>/.claude/output-styles/
  * user scope:     ~/.claude/output-styles/

Usage:
    python install_styles.py                 # into ./.claude/output-styles/
    python install_styles.py --user          # into ~/.claude/output-styles/
    python install_styles.py --target DIR    # into DIR/.claude/output-styles/
    python install_styles.py --list          # just list bundled styles
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

STYLES_DIR = Path(__file__).resolve().parent.parent / "output-styles"


def bundled_styles() -> list[Path]:
    if not STYLES_DIR.is_dir():
        return []
    return sorted(STYLES_DIR.glob("*.md"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="install tokenwise output styles")
    ap.add_argument("--user", action="store_true", help="install to ~/.claude")
    ap.add_argument("--target", default=".", help="project dir (default: cwd)")
    ap.add_argument("--list", action="store_true", help="list bundled styles and exit")
    args = ap.parse_args(argv)

    styles = bundled_styles()
    if not styles:
        print("error: no bundled output styles found next to this script", file=sys.stderr)
        return 1

    if args.list:
        print("Bundled output styles:")
        for s in styles:
            print(f"  - {s.stem}")
        return 0

    base = Path.home() if args.user else Path(args.target).resolve()
    dest = base / ".claude" / "output-styles"
    dest.mkdir(parents=True, exist_ok=True)

    for s in styles:
        shutil.copy2(s, dest / s.name)
        print(f"installed {s.name} -> {dest / s.name}")

    print()
    print(f"Done. Activate one with:  /output-style {styles[0].stem.lower()}")
    print("Reset to default with:    /output-style default")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
