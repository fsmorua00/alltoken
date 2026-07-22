#!/usr/bin/env python3
"""
tokenwise audit — deterministic token-waste analysis for a project.

Scans the things that silently inflate every Claude Code session before you
type a single word: CLAUDE.md size, configured MCP servers, skill descriptions,
and settings. Produces an estimated "context floor" (tokens loaded up front)
plus concrete, ranked recommendations.

No network, no model calls — pure static analysis. Token counts are estimates
based on a ~4-chars-per-token heuristic, not exact tokenizer output.

Usage:
    python audit.py [--root DIR] [--json] [--include-user]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path

CHARS_PER_TOKEN = 4  # rough, tokenizer-agnostic heuristic

# Thresholds (tuned to Anthropic's public guidance + practical experience)
CLAUDE_MD_MAX_LINES = 200
CLAUDE_MD_MAX_TOKENS = 2500
SKILL_DESC_MAX_CHARS = 500
MCP_SERVER_SOFT_LIMIT = 4
# Very rough per-server context cost (tool schemas + instructions). It varies a
# lot by server; treated as an estimate and labelled as such in the report.
MCP_SERVER_EST_TOKENS = 700


def est_tokens(text: str) -> int:
    if not text:
        return 0
    return (len(text) + CHARS_PER_TOKEN - 1) // CHARS_PER_TOKEN


@dataclass
class Finding:
    severity: str  # "high" | "medium" | "low" | "info"
    area: str
    message: str
    est_tokens: int = 0
    fix: str = ""


@dataclass
class Report:
    root: str
    context_floor_tokens: int = 0
    potential_savings_tokens: int = 0
    findings: list[Finding] = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    def add(self, f: Finding) -> None:
        self.findings.append(f)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


# --------------------------------------------------------------------------- #
# CLAUDE.md
# --------------------------------------------------------------------------- #
def scan_claude_md(root: Path, report: Report, include_user: bool) -> int:
    candidates = [
        root / "CLAUDE.md",
        root / ".claude" / "CLAUDE.md",
        root / "CLAUDE.local.md",
    ]
    if include_user:
        candidates.append(Path.home() / ".claude" / "CLAUDE.md")

    total = 0
    found_any = False
    for path in candidates:
        if not path.is_file():
            continue
        found_any = True
        text = read_text(path)
        lines = text.count("\n") + 1
        tokens = est_tokens(text)
        total += tokens
        label = str(path)
        if lines > CLAUDE_MD_MAX_LINES or tokens > CLAUDE_MD_MAX_TOKENS:
            report.add(
                Finding(
                    severity="high",
                    area="CLAUDE.md",
                    message=(
                        f"{label} is {lines} lines / ~{tokens} tokens — over the "
                        f"{CLAUDE_MD_MAX_LINES}-line guideline. This is re-injected "
                        f"context on every turn."
                    ),
                    est_tokens=max(0, tokens - CLAUDE_MD_MAX_TOKENS),
                    fix=(
                        "Trim to a lean directory of project conventions. Move "
                        "long docs/examples out to files Claude reads on demand."
                    ),
                )
            )
        else:
            report.add(
                Finding(
                    severity="info",
                    area="CLAUDE.md",
                    message=f"{label}: {lines} lines / ~{tokens} tokens (within budget).",
                    est_tokens=0,
                )
            )
    if not found_any:
        report.add(
            Finding(
                severity="info",
                area="CLAUDE.md",
                message="No CLAUDE.md found in project. Nothing to trim here.",
            )
        )
    report.stats["claude_md_tokens"] = total
    return total


# --------------------------------------------------------------------------- #
# MCP servers
# --------------------------------------------------------------------------- #
def _collect_mcp_servers(root: Path) -> dict:
    servers: dict[str, str] = {}
    sources = [
        root / ".mcp.json",
        root / ".claude" / "settings.json",
        root / ".claude" / "settings.local.json",
    ]
    for path in sources:
        if not path.is_file():
            continue
        try:
            data = json.loads(read_text(path) or "{}")
        except json.JSONDecodeError:
            continue
        block = data.get("mcpServers") or data.get("mcp_servers") or {}
        if isinstance(block, dict):
            for name in block:
                servers[name] = str(path)
    return servers


def scan_mcp(root: Path, report: Report) -> int:
    servers = _collect_mcp_servers(root)
    count = len(servers)
    report.stats["mcp_servers"] = count
    if count == 0:
        report.add(
            Finding(
                severity="info",
                area="MCP",
                message="No project-level MCP servers configured.",
            )
        )
        return 0

    est = count * MCP_SERVER_EST_TOKENS
    severity = "medium" if count > MCP_SERVER_SOFT_LIMIT else "info"
    names = ", ".join(sorted(servers))
    report.add(
        Finding(
            severity=severity,
            area="MCP",
            message=(
                f"{count} MCP server(s) configured ({names}). Each loads tool "
                f"schemas into context (~{MCP_SERVER_EST_TOKENS} tok/server est.)."
            ),
            est_tokens=est,
            fix=(
                "Disconnect servers you don't actively use. Run `/mcp` to review. "
                "Every connected server pays context rent on every session."
            ),
        )
    )
    return est


# --------------------------------------------------------------------------- #
# Skills
# --------------------------------------------------------------------------- #
_DESC_RE = re.compile(r"^description:\s*(.*)$", re.IGNORECASE | re.MULTILINE)


def _extract_frontmatter_desc(text: str) -> str:
    # SKILL.md uses YAML frontmatter between --- fences.
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            fm = text[3:end]
            m = _DESC_RE.search(fm)
            if m:
                return m.group(1).strip().strip("'\"")
    m = _DESC_RE.search(text)
    return m.group(1).strip().strip("'\"") if m else ""


def scan_skills(root: Path, report: Report) -> int:
    skill_dirs = [root / ".claude" / "skills"]
    total = 0
    count = 0
    for base in skill_dirs:
        if not base.is_dir():
            continue
        for skill_md in base.glob("*/SKILL.md"):
            count += 1
            text = read_text(skill_md)
            desc = _extract_frontmatter_desc(text)
            dtok = est_tokens(desc)
            total += dtok
            if len(desc) > SKILL_DESC_MAX_CHARS:
                report.add(
                    Finding(
                        severity="medium",
                        area="skills",
                        message=(
                            f"Skill '{skill_md.parent.name}' has a long description "
                            f"({len(desc)} chars / ~{dtok} tok). Descriptions load "
                            f"into context every session."
                        ),
                        est_tokens=max(0, dtok - est_tokens("x" * SKILL_DESC_MAX_CHARS)),
                        fix="Tighten the description to the trigger conditions only.",
                    )
                )
    report.stats["skills"] = count
    report.stats["skill_desc_tokens"] = total
    if count == 0:
        report.add(
            Finding(
                severity="info",
                area="skills",
                message="No project-level skills found (.claude/skills/).",
            )
        )
    return total


# --------------------------------------------------------------------------- #
# Settings / output verbosity signals
# --------------------------------------------------------------------------- #
def scan_output_style(root: Path, report: Report) -> None:
    """Detect whether a concise-output convention is already in place."""
    signals = []
    for path in [root / "CLAUDE.md", root / ".claude" / "CLAUDE.md"]:
        if path.is_file():
            text = read_text(path).lower()
            if "concise" in text or "be brief" in text or "few words" in text:
                signals.append(str(path))
    if signals:
        report.add(
            Finding(
                severity="info",
                area="output",
                message="Concise-output instruction already present in CLAUDE.md.",
            )
        )
    else:
        report.add(
            Finding(
                severity="low",
                area="output",
                message="No concise-output convention detected.",
                fix=(
                    "Add a short 'be concise' rule to CLAUDE.md, or run "
                    "`/token-optimize` to install one. Small but free win."
                ),
            )
        )


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def run(root: Path, include_user: bool) -> Report:
    report = Report(root=str(root))
    floor = 0
    floor += scan_claude_md(root, report, include_user)
    floor += scan_mcp(root, report)
    floor += scan_skills(root, report)
    scan_output_style(root, report)

    report.context_floor_tokens = floor
    report.potential_savings_tokens = sum(
        f.est_tokens for f in report.findings if f.severity in ("high", "medium")
    )
    # Rank findings: high > medium > low > info
    order = {"high": 0, "medium": 1, "low": 2, "info": 3}
    report.findings.sort(key=lambda f: (order.get(f.severity, 9), -f.est_tokens))
    return report


SEV_ICON = {"high": "🔴", "medium": "🟡", "low": "🔵", "info": "⚪"}


def render_human(report: Report) -> str:
    out = []
    out.append("═" * 64)
    out.append("  tokenwise audit")
    out.append(f"  project: {report.root}")
    out.append("═" * 64)
    out.append("")
    out.append(
        f"  Estimated context floor: ~{report.context_floor_tokens:,} tokens "
        f"loaded before your first message."
    )
    out.append(
        f"  Addressable waste (high+medium): ~{report.potential_savings_tokens:,} tokens/session."
    )
    out.append("")
    s = report.stats
    out.append(
        f"  Stats: CLAUDE.md ~{s.get('claude_md_tokens', 0)} tok · "
        f"{s.get('mcp_servers', 0)} MCP server(s) · "
        f"{s.get('skills', 0)} skill(s)"
    )
    out.append("")
    out.append("  Findings (most impactful first):")
    out.append("  " + "-" * 60)
    for f in report.findings:
        icon = SEV_ICON.get(f.severity, "•")
        tag = f" (~{f.est_tokens} tok)" if f.est_tokens else ""
        out.append(f"  {icon} [{f.area}]{tag} {f.message}")
        if f.fix:
            out.append(f"       ↳ fix: {f.fix}")
    out.append("")
    out.append("  Note: token counts are ~4-chars/token estimates, not exact.")
    out.append("  Run `/token-optimize` to apply the safe fixes automatically.")
    out.append("═" * 64)
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="tokenwise deterministic audit")
    ap.add_argument("--root", default=os.getcwd(), help="project root (default: cwd)")
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    ap.add_argument(
        "--include-user",
        action="store_true",
        help="also inspect ~/.claude/CLAUDE.md (user-level context)",
    )
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 2

    report = run(root, args.include_user)

    if args.json:
        payload = asdict(report)
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(render_human(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
