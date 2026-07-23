#!/usr/bin/env python3
"""
alltoken ghost-skills — find skills that pay rent but never work.

Every installed skill's DESCRIPTION loads into context on every session — a
fixed rent. The body is free until invoked (lazy-loaded by the platform). So
the real waste isn't big skills: it's skills that NEVER FIRE. Pure rent, zero
work. This module cross-references:

  * installed skills (project `.claude/skills/`, optionally user `~/.claude/skills/`)
  * actual invocations mined from Claude Code's local JSONL logs
    (Skill tool_use blocks + <command-name> slash invocations)

…and reports, per skill: estimated rent (tokens/session), how many times it
actually ran, when it last ran, and a verdict:

  👻 GHOST   never invoked in available logs → remove or archive
  ✂️ TRIM    used, but the description is bloated → tighten to trigger conditions
  ✔ ACTIVE  earning its rent

Honest caveat baked into the output: local logs only go back as far as they go
— a skill can look ghostly just because the logs are young. The report states
the observation window it actually had.

Usage:
    python ghost_skills.py [--root DIR] [--include-user] [--json]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import audit  # noqa: E402  (est_tokens, frontmatter description parser)
import usage_stats  # noqa: E402  (default_projects_dir)

CMD_RE = re.compile(r"<command-name>\s*/?([^<\s]+)\s*</command-name>")
DESC_TRIM_CHARS = 500  # same threshold the audit uses


def norm(name: str) -> str:
    """Normalize a skill/command reference to its base name."""
    name = name.strip().lstrip("/")
    if ":" in name:
        name = name.rsplit(":", 1)[-1]
    return name.lower()


# --------------------------------------------------------------------------- #
# Installed skills inventory
# --------------------------------------------------------------------------- #
def inventory(root: Path, include_user: bool) -> list[dict]:
    bases = [("project", root / ".claude" / "skills")]
    if include_user:
        bases.append(("user", Path.home() / ".claude" / "skills"))
    skills: list[dict] = []
    for scope, base in bases:
        if not base.is_dir():
            continue
        for skill_md in sorted(base.glob("*/SKILL.md")):
            text = skill_md.read_text(encoding="utf-8", errors="replace")
            desc = audit._extract_frontmatter_desc(text)
            m = re.search(r"^name:\s*(.+)$", text[:400], re.MULTILINE)
            name = (m.group(1).strip() if m else skill_md.parent.name)
            skills.append(
                {
                    "name": name,
                    "key": norm(name),
                    "scope": scope,
                    "path": str(skill_md),
                    "desc_chars": len(desc),
                    "rent_tokens": audit.est_tokens(desc),
                }
            )
    return skills


# --------------------------------------------------------------------------- #
# Usage mining from local logs
# --------------------------------------------------------------------------- #
def mine_usage(projects_dir: Path) -> tuple[dict[str, dict], str]:
    """Return {skill_key: {uses, last_day}} and the oldest log day seen."""
    uses: dict[str, dict] = {}
    oldest = ""

    def record(name: str, day: str) -> None:
        key = norm(name)
        if not key:
            return
        u = uses.setdefault(key, {"uses": 0, "last_day": ""})
        u["uses"] += 1
        u["last_day"] = max(u["last_day"], day)

    for jsonl in projects_dir.glob("**/*.jsonl"):
        try:
            with jsonl.open("r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if "SKILL" not in line and "Skill" not in line and "command-name" not in line:
                        continue
                    day = ""
                    try:
                        entry = json.loads(line)
                        day = str(entry.get("timestamp") or "")[:10]
                        if day and (not oldest or day < oldest):
                            oldest = day
                        msg = entry.get("message")
                        content = msg.get("content") if isinstance(msg, dict) else None
                        if isinstance(content, list):
                            for block in content:
                                if (
                                    isinstance(block, dict)
                                    and block.get("type") == "tool_use"
                                    and block.get("name") == "Skill"
                                ):
                                    record(str((block.get("input") or {}).get("skill") or ""), day)
                    except json.JSONDecodeError:
                        pass
                    for m in CMD_RE.finditer(line):
                        record(m.group(1), day)
        except OSError:
            continue
    return uses, oldest


# --------------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------------- #
def build_report(root: Path, include_user: bool) -> dict:
    skills = inventory(root, include_user)
    projects_dir = usage_stats.default_projects_dir()
    if projects_dir.is_dir():
        uses, oldest = mine_usage(projects_dir)
    else:
        uses, oldest = {}, ""

    for s in skills:
        u = uses.get(s["key"], {"uses": 0, "last_day": ""})
        s["uses"] = u["uses"]
        s["last_used"] = u["last_day"] or None
        if u["uses"] == 0:
            s["verdict"] = "ghost"
        elif s["desc_chars"] > DESC_TRIM_CHARS:
            s["verdict"] = "trim"
        else:
            s["verdict"] = "active"

    ghost_rent = sum(s["rent_tokens"] for s in skills if s["verdict"] == "ghost")
    return {
        "root": str(root),
        "logs_since": oldest or None,
        "skills": sorted(skills, key=lambda s: (s["verdict"] != "ghost", -s["rent_tokens"])),
        "ghost_rent_tokens_per_session": ghost_rent,
    }


ICON = {"ghost": "👻", "trim": "✂️", "active": "✔"}


def render(rep: dict) -> str:
    out = []
    out.append("═" * 64)
    out.append("  alltoken ghost-skills — who pays rent but never works?")
    out.append(f"  project: {rep['root']}")
    if rep["logs_since"]:
        out.append(f"  observation window: local logs since {rep['logs_since']}")
    else:
        out.append("  observation window: NO LOGS FOUND — every skill will look ghostly; don't act on this run.")
    out.append("═" * 64)
    if not rep["skills"]:
        out.append("  No skills installed at project scope. (Try --include-user.)")
        out.append("═" * 64)
        return "\n".join(out)

    for s in rep["skills"]:
        used = f"{s['uses']} use(s), last {s['last_used']}" if s["uses"] else "never invoked"
        out.append(
            f"  {ICON[s['verdict']]} {s['name']} [{s['scope']}] — rent ~{s['rent_tokens']} tok/session · {used}"
        )
        if s["verdict"] == "ghost":
            out.append("       ↳ pure rent: remove it, or archive outside .claude/skills/ until needed.")
        elif s["verdict"] == "trim":
            out.append(f"       ↳ earning rent, but description is {s['desc_chars']} chars — tighten to trigger conditions.")
    out.append("")
    out.append(
        f"  ghost rent total: ~{rep['ghost_rent_tokens_per_session']} tok/session, every session, for nothing."
    )
    out.append("  caveat: young/cleaned logs make skills look ghostly — check the window above.")
    out.append("═" * 64)
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="alltoken ghost-skill detector")
    ap.add_argument("--root", default=".", help="project root (default: cwd)")
    ap.add_argument("--include-user", action="store_true", help="also scan ~/.claude/skills")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 2

    rep = build_report(root, args.include_user)
    if args.json:
        print(json.dumps(rep, indent=2, ensure_ascii=False))
    else:
        print(render(rep))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
