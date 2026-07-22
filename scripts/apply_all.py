#!/usr/bin/env python3
"""
tokenwise apply-all — the /alltoken engine: apply every safe token-saving
technique to a project in ONE shot.

Deterministic parts only (no model, no network):
  1. audit the project (before snapshot)
  2. install the bundled output styles into <root>/.claude/output-styles/
  3. activate one style via .claude/settings.local.json ("outputStyle" key)
  4. inject/update an idempotent "token discipline" block in CLAUDE.md that
     encodes Anthropic's official best practices — so EVERY future session in
     the project loads them automatically
  5. audit again (after snapshot) and summarize what changed and what still
     needs a human decision

Judgment parts (trimming a bloated CLAUDE.md, disconnecting MCP servers) are
left to the /alltoken command's Claude layer — this script never deletes or
relocates user content. Re-running is safe: the block updates in place, styles
are re-copied, settings are merged (never clobbered).

Usage:
    python apply_all.py [--root DIR] [--style concise|caveman|telegraphic]
                        [--shared] [--no-activate] [--json]
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import audit  # noqa: E402  (local module)

STYLES_DIR = HERE.parent / "output-styles"

MARK_START = "<!-- tokenwise:start -->"
MARK_END = "<!-- tokenwise:end -->"

BLOCK_BODY = """## Token discipline (tokenwise — auto-managed; run /alltoken to refresh)
- Be concise: answer directly; no preamble/postamble; bullets and code over prose.
- Read only what's needed: targeted search/partial reads over whole files;
  batch independent tool calls in parallel.
- Route grunt work (format/summarize/extract/fetch) to the cheapest capable
  model via a haiku subagent; reserve the frontier model for real judgment
  (see skill: minimum-viable-model).
- Prefer deterministic scripts over re-prompting for repeatable transformations.
- Context hygiene: /clear between unrelated tasks; /compact before context fills.
- Keep CLAUDE.md under ~200 lines; long docs live in files read on demand.
- Official guidance: https://www.anthropic.com/engineering/claude-code-best-practices
"""

BLOCK_CORE = f"{MARK_START}\n{BLOCK_BODY}{MARK_END}"

_NAME_RE = re.compile(r"^name:\s*(.+)$", re.MULTILINE)


def display_name(style_path: Path) -> str:
    m = _NAME_RE.search(style_path.read_text(encoding="utf-8", errors="replace"))
    return m.group(1).strip() if m else style_path.stem.capitalize()


# --------------------------------------------------------------------------- #
# Step: CLAUDE.md discipline block (idempotent)
# --------------------------------------------------------------------------- #
def ensure_block(root: Path) -> tuple[str, str]:
    """Insert or refresh the marked block. Returns (action, path-str)."""
    target = root / "CLAUDE.md"
    alt = root / ".claude" / "CLAUDE.md"
    if not target.is_file() and alt.is_file():
        target = alt

    if not target.is_file():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(BLOCK_CORE + "\n", encoding="utf-8")
        return "created", str(target)

    text = target.read_text(encoding="utf-8", errors="replace")
    if MARK_START in text and MARK_END in text:
        pre = text.split(MARK_START, 1)[0]
        post = text.split(MARK_END, 1)[1]
        new = pre + BLOCK_CORE + post
        if new == text:
            return "unchanged", str(target)
        target.write_text(new, encoding="utf-8")
        return "updated", str(target)

    new = text.rstrip("\n") + "\n\n" + BLOCK_CORE + "\n"
    target.write_text(new, encoding="utf-8")
    return "appended", str(target)


# --------------------------------------------------------------------------- #
# Step: install output styles into the project
# --------------------------------------------------------------------------- #
def install_project_styles(root: Path) -> list[str]:
    dest = root / ".claude" / "output-styles"
    dest.mkdir(parents=True, exist_ok=True)
    names: list[str] = []
    for s in sorted(STYLES_DIR.glob("*.md")):
        shutil.copy2(s, dest / s.name)
        names.append(display_name(s))
    return names


# --------------------------------------------------------------------------- #
# Step: activate a style via settings (merge, never clobber)
# --------------------------------------------------------------------------- #
def activate_style(root: Path, style_key: str, shared: bool) -> tuple[str, str]:
    style_file = STYLES_DIR / f"{style_key}.md"
    if not style_file.is_file():
        avail = ", ".join(p.stem for p in sorted(STYLES_DIR.glob("*.md")))
        return "error", f"unknown style '{style_key}' (available: {avail})"

    name = display_name(style_file)
    settings = root / ".claude" / ("settings.json" if shared else "settings.local.json")

    data: dict = {}
    if settings.is_file():
        try:
            loaded = json.loads(settings.read_text(encoding="utf-8") or "{}")
        except json.JSONDecodeError:
            return "skipped", f"{settings} has invalid JSON — not touching it"
        if not isinstance(loaded, dict):
            return "skipped", f"{settings} is not a JSON object — not touching it"
        data = loaded

    prev = data.get("outputStyle")
    if prev == name:
        return "unchanged", f"outputStyle already '{name}' in {settings.name}"

    data["outputStyle"] = name
    settings.parent.mkdir(parents=True, exist_ok=True)
    settings.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return "set", f"outputStyle: {prev or '(none)'} → '{name}' in {settings.name}"


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="tokenwise one-shot applier (/alltoken)")
    ap.add_argument("--root", default=".", help="project root (default: cwd)")
    ap.add_argument(
        "--style",
        default="concise",
        help="output style to activate: concise|caveman|telegraphic (default: concise)",
    )
    ap.add_argument(
        "--shared",
        action="store_true",
        help="write outputStyle to settings.json (team-wide) instead of settings.local.json",
    )
    ap.add_argument("--no-activate", action="store_true", help="install styles but don't activate any")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 2

    before = audit.run(root, include_user=False)

    styles = install_project_styles(root)
    if args.no_activate:
        act_status, act_msg = "skipped", "style activation disabled (--no-activate)"
    else:
        act_status, act_msg = activate_style(root, args.style.lower(), args.shared)
    block_status, block_path = ensure_block(root)
    block_tokens = audit.est_tokens(BLOCK_CORE)

    after = audit.run(root, include_user=False)
    remaining = [
        {"severity": f.severity, "area": f.area, "message": f.message, "fix": f.fix}
        for f in after.findings
        if f.severity in ("high", "medium")
    ][:5]

    if args.json:
        print(
            json.dumps(
                {
                    "root": str(root),
                    "before_floor_tokens": before.context_floor_tokens,
                    "after_floor_tokens": after.context_floor_tokens,
                    "styles_installed": styles,
                    "style_activation": {"status": act_status, "detail": act_msg},
                    "claude_md_block": {
                        "status": block_status,
                        "path": block_path,
                        "est_tokens": block_tokens,
                    },
                    "needs_human_decision": remaining,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    ok = "✔"
    print("═" * 64)
    print("  tokenwise · /alltoken (one-shot)")
    print(f"  project: {root}")
    print("═" * 64)
    print(f"  before: context floor ~{before.context_floor_tokens:,} tok")
    print()
    print(f"  {ok} output styles installed: {', '.join(styles)}  (.claude/output-styles/)")
    print(f"  {ok} style activation [{act_status}]: {act_msg}")
    print(
        f"  {ok} CLAUDE.md discipline block [{block_status}] at {block_path} "
        f"(~{block_tokens} tok/session — buys official-best-practice enforcement "
        f"on every session)"
    )
    print()
    print(f"  after:  context floor ~{after.context_floor_tokens:,} tok")
    print(
        "  note: OUTPUT-token savings from the response style don't show in the "
        "floor number — the floor measures preloaded INPUT context."
    )
    if remaining:
        print()
        print("  needs your call (not auto-applied):")
        for r in remaining:
            print(f"    • [{r['area']}] {r['message']}")
            if r["fix"]:
                print(f"      ↳ {r['fix']}")
    print()
    print("  revert: /output-style default · git diff/checkout for file changes")
    print("═" * 64)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
