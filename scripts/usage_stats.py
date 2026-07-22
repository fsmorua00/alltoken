#!/usr/bin/env python3
"""
alltoken usage — local token-usage analytics from Claude Code's own JSONL logs.

Inspired by the excellent ccusage (github.com/ryoppippi/ccusage, ~16k stars);
this is a minimal, dependency-free, deterministic subset bundled with alltoken
so /token-usage works out of the box. For full cost reports, live dashboards and
multi-agent support, use ccusage itself (`npx ccusage@latest`).

Reads ~/.claude/projects/**/*.jsonl (never sends data anywhere), deduplicates
streamed entries by message id, and reports where your tokens actually go:
by model, by day, and input vs output vs cache. That answers the three questions
that matter for optimization:
  * Which model burns most?      → minimum-viable-model routing
  * How big is the output share? → output styles (concise/caveman)
  * How good is my cache ratio?  → focused work blocks vs trickled sessions

Usage:
    python usage_stats.py [--dir DIR] [--days N] [--json]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path


def default_projects_dir() -> Path:
    cfg = os.environ.get("CLAUDE_CONFIG_DIR")
    base = Path(cfg) if cfg else Path.home() / ".claude"
    return base / "projects"


def iter_usage_entries(projects_dir: Path):
    """Yield (msg_id, model, day, usage_dict) for every assistant entry."""
    for jsonl in sorted(projects_dir.glob("**/*.jsonl")):
        try:
            with jsonl.open("r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    msg = entry.get("message")
                    if not isinstance(msg, dict):
                        continue
                    usage = msg.get("usage")
                    if not isinstance(usage, dict):
                        continue
                    model = msg.get("model") or "unknown"
                    if model == "<synthetic>":
                        continue
                    ts = str(entry.get("timestamp") or "")
                    day = ts[:10] if len(ts) >= 10 else "unknown"
                    msg_id = msg.get("id")
                    yield msg_id, model, day, usage
        except OSError:
            continue


def munge_project_path(root: Path) -> str:
    """Claude Code names each project's log dir by munging its absolute path."""
    return "".join(c if c.isalnum() else "-" for c in str(root))


def find_project_dir(projects_dir: Path, root: Path) -> Path | None:
    """Locate the per-project log dir for `root`, tolerating munging variants."""
    want = munge_project_path(root.resolve())
    exact = projects_dir / want
    if exact.is_dir():
        return exact
    for d in projects_dir.iterdir():
        if d.is_dir() and d.name.lower() == want.lower():
            return d
    return None


def collect(
    projects_dir: Path,
    days: int,
    since: str = "",
    until: str = "",
) -> dict:
    """Aggregate usage. `since`/`until` are inclusive ISO dates (YYYY-MM-DD)
    that override/augment the rolling `days` window when provided."""
    cutoff = (date.today() - timedelta(days=days)).isoformat() if days > 0 else ""
    if since:
        cutoff = max(cutoff, since) if cutoff else since

    # Streaming writes repeat the same message id with cumulative usage;
    # keep the LAST occurrence per id (matches how the final chunk reports).
    latest: dict[str, tuple[str, str, dict]] = {}
    anon: list[tuple[str, str, dict]] = []
    for msg_id, model, day, usage in iter_usage_entries(projects_dir):
        if cutoff and day != "unknown" and day < cutoff:
            continue
        if until and day != "unknown" and day > until:
            continue
        if msg_id:
            latest[msg_id] = (model, day, usage)
        else:
            anon.append((model, day, usage))

    per_model: dict[str, dict] = defaultdict(
        lambda: {"input": 0, "output": 0, "cache_create": 0, "cache_read": 0, "messages": 0}
    )
    per_day: dict[str, dict] = defaultdict(lambda: {"input": 0, "output": 0})
    totals = {"input": 0, "output": 0, "cache_create": 0, "cache_read": 0, "messages": 0}

    for model, day, usage in list(latest.values()) + anon:
        i = int(usage.get("input_tokens") or 0)
        o = int(usage.get("output_tokens") or 0)
        cc = int(usage.get("cache_creation_input_tokens") or 0)
        cr = int(usage.get("cache_read_input_tokens") or 0)
        m = per_model[model]
        m["input"] += i
        m["output"] += o
        m["cache_create"] += cc
        m["cache_read"] += cr
        m["messages"] += 1
        d = per_day[day]
        d["input"] += i + cc + cr
        d["output"] += o
        totals["input"] += i
        totals["output"] += o
        totals["cache_create"] += cc
        totals["cache_read"] += cr
        totals["messages"] += 1

    return {"per_model": dict(per_model), "per_day": dict(per_day), "totals": totals}


def fmt(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def render(data: dict, projects_dir: Path, days: int) -> str:
    t = data["totals"]
    out = []
    out.append("═" * 64)
    out.append("  alltoken usage — local logs, nothing leaves your machine")
    out.append(f"  source: {projects_dir}  ·  window: last {days} day(s)")
    out.append("═" * 64)
    if t["messages"] == 0:
        out.append("  No usage entries found. (New machine, cleaned logs, or a")
        out.append("  non-default CLAUDE_CONFIG_DIR — try --dir.)")
        out.append("═" * 64)
        return "\n".join(out)

    input_side = t["input"] + t["cache_create"] + t["cache_read"]
    grand = input_side + t["output"]
    cache_share = (100 * t["cache_read"] / input_side) if input_side else 0
    out_share = (100 * t["output"] / grand) if grand else 0

    out.append(f"  totals: {fmt(grand)} tokens across {t['messages']} assistant messages")
    out.append(
        f"    input {fmt(t['input'])} · cache-write {fmt(t['cache_create'])} · "
        f"cache-read {fmt(t['cache_read'])} · output {fmt(t['output'])}"
    )
    out.append(f"    cache-read share of input side: {cache_share:.0f}%   ·   output share: {out_share:.0f}%")
    out.append("")
    out.append("  by model:")
    ranked = sorted(
        data["per_model"].items(),
        key=lambda kv: -(kv[1]["input"] + kv[1]["cache_create"] + kv[1]["cache_read"] + kv[1]["output"]),
    )
    for model, m in ranked[:8]:
        tot = m["input"] + m["cache_create"] + m["cache_read"] + m["output"]
        out.append(f"    {fmt(tot):>8}  {model}  ({m['messages']} msgs, out {fmt(m['output'])})")
    out.append("")
    out.append("  reading the numbers:")
    if cache_share < 40:
        out.append("    • cache-read share is LOW → work in focused blocks; long pauses expire the cache.")
    else:
        out.append("    • cache-read share is healthy — focused-block habit is working.")
    if out_share > 20:
        out.append("    • output share is HIGH → a concise output style pays off (/alltoken caveman).")
    frontier_heavy = ranked and ("haiku" not in ranked[0][0].lower()) and len(ranked) >= 1
    if frontier_heavy:
        out.append("    • top spender is a frontier model → route grunt work to haiku (minimum-viable-model).")
    out.append("")
    out.append("  full cost reports & dashboards: npx ccusage@latest (ryoppippi/ccusage)")
    out.append("═" * 64)
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="alltoken local usage analytics")
    ap.add_argument("--dir", default=None, help="projects dir (default: ~/.claude/projects)")
    ap.add_argument("--days", type=int, default=30, help="window in days (default 30; 0 = all)")
    ap.add_argument("--project", default=None, help="only this project's logs (pass its path)")
    ap.add_argument("--since", default="", help="inclusive start date YYYY-MM-DD")
    ap.add_argument("--until", default="", help="inclusive end date YYYY-MM-DD")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args(argv)

    projects_dir = Path(args.dir) if args.dir else default_projects_dir()
    if not projects_dir.is_dir():
        print(f"error: {projects_dir} not found — is this machine running Claude Code?", file=sys.stderr)
        return 2

    if args.project:
        sub = find_project_dir(projects_dir, Path(args.project))
        if sub is None:
            print(f"error: no logs found for project {args.project}", file=sys.stderr)
            return 2
        projects_dir = sub

    data = collect(projects_dir, args.days, since=args.since, until=args.until)
    if args.json:
        print(json.dumps(data, indent=2))
    else:
        print(render(data, projects_dir, args.days))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
