#!/usr/bin/env python3
"""
alltoken progress — prove (or disprove) your savings with your own data.

Everyone in this niche CLAIMS savings; nobody measures them on the user's own
logs. This module closes that loop:

  save    Snapshot a baseline of your usage metrics at /alltoken time
          (stored in <project>/.claude/alltoken/baseline.json).
  report  Compare usage since the baseline against the baseline window and
          show honest deltas.

Metrics (all derived locally from Claude Code's own JSONL logs):
  * tokens per assistant message (grand total / messages)
  * output share  (output tokens / grand total)
  * cache-read share (cache reads / input side)
  * frontier share (non-haiku tokens / grand total)

Honest by design: workload changes move these numbers too. This is YOUR data,
not a controlled experiment — the report says so explicitly. Nothing is sent
anywhere; sharing aggregates with the community benchmark is a separate,
explicit opt-in (see share_stats.py and docs/telemetry.md).

Usage:
    python progress.py save   [--root DIR] [--force | --if-missing]
    python progress.py report [--root DIR] [--json]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import usage_stats  # noqa: E402  (local module)

BASELINE_WINDOW_DAYS = 30  # usage window captured as the "before" picture


def baseline_path(root: Path) -> Path:
    return root / ".claude" / "alltoken" / "baseline.json"


def metrics_from(data: dict) -> dict:
    t = data["totals"]
    input_side = t["input"] + t["cache_create"] + t["cache_read"]
    grand = input_side + t["output"]
    msgs = t["messages"]
    frontier_tok = 0
    for model, m in data["per_model"].items():
        if "haiku" not in model.lower():
            frontier_tok += m["input"] + m["cache_create"] + m["cache_read"] + m["output"]
    return {
        "messages": msgs,
        "total_tokens": grand,
        "tok_per_msg": round(grand / msgs) if msgs else 0,
        "output_share_pct": round(100 * t["output"] / grand, 1) if grand else 0.0,
        "cache_read_share_pct": round(100 * t["cache_read"] / input_side, 1) if input_side else 0.0,
        "frontier_share_pct": round(100 * frontier_tok / grand, 1) if grand else 0.0,
    }


def project_usage(root: Path, days: int, since: str = "", until: str = "") -> dict | None:
    projects_dir = usage_stats.default_projects_dir()
    if not projects_dir.is_dir():
        return None
    sub = usage_stats.find_project_dir(projects_dir, root)
    scope = sub if sub is not None else projects_dir
    data = usage_stats.collect(scope, days, since=since, until=until)
    data["scope"] = "project" if sub is not None else "all-projects"
    return data


# --------------------------------------------------------------------------- #
# save
# --------------------------------------------------------------------------- #
def cmd_save(root: Path, force: bool, if_missing: bool) -> int:
    bp = baseline_path(root)
    if bp.is_file() and not force:
        if if_missing:
            print(f"baseline already exists ({bp}) — keeping it.")
            return 0
        print(f"error: baseline already exists at {bp} (use --force to overwrite)", file=sys.stderr)
        return 1

    data = project_usage(root, BASELINE_WINDOW_DAYS)
    if data is None:
        print("error: no Claude Code logs found on this machine — nothing to baseline.", file=sys.stderr)
        return 2

    m = metrics_from(data)
    payload = {
        "schema": 1,
        "saved_on": date.today().isoformat(),
        "window_days": BASELINE_WINDOW_DAYS,
        "scope": data["scope"],
        "metrics": m,
    }
    bp.parent.mkdir(parents=True, exist_ok=True)
    bp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(
        f"baseline saved → {bp}\n"
        f"  window: last {BASELINE_WINDOW_DAYS} days ({data['scope']}), "
        f"{m['messages']} messages, ~{m['tok_per_msg']:,} tok/msg, "
        f"output {m['output_share_pct']}%, cache-read {m['cache_read_share_pct']}%, "
        f"frontier {m['frontier_share_pct']}%"
    )
    if m["messages"] < 20:
        print("  note: small sample — deltas will be noisy until you have more usage.")
    return 0


# --------------------------------------------------------------------------- #
# report
# --------------------------------------------------------------------------- #
def delta_str(before: float, after: float, lower_is_better: bool, unit: str = "") -> str:
    if before == 0:
        return "n/a (empty baseline)"
    diff = after - before
    pct = 100 * diff / before
    arrow = "↓" if diff < 0 else ("↑" if diff > 0 else "=")
    good = (diff < 0) == lower_is_better if diff != 0 else True
    tag = "better" if good else "worse"
    if diff == 0:
        tag = "same"
    return f"{arrow} {abs(pct):.0f}% ({tag}){unit and ' ' + unit}"


def cmd_report(root: Path, as_json: bool) -> int:
    bp = baseline_path(root)
    if not bp.is_file():
        print(
            "No baseline for this project yet. Run:\n"
            "    python3 scripts/progress.py save\n"
            "(or /alltoken, which saves one automatically the first time).",
            file=sys.stderr,
        )
        return 1
    base = json.loads(bp.read_text(encoding="utf-8"))
    saved_on = base["saved_on"]
    since = (date.fromisoformat(saved_on) + timedelta(days=1)).isoformat()

    data = project_usage(root, days=0, since=since)
    if data is None:
        print("error: no Claude Code logs found on this machine.", file=sys.stderr)
        return 2
    after = metrics_from(data)
    before = base["metrics"]
    days_elapsed = (date.today() - date.fromisoformat(saved_on)).days

    result = {
        "baseline_date": saved_on,
        "days_since_baseline": days_elapsed,
        "scope": data["scope"],
        "before": before,
        "after": after,
    }
    if as_json:
        print(json.dumps(result, indent=2))
        return 0

    print("═" * 64)
    print("  alltoken progress — your own data, before vs after")
    print(f"  baseline: {saved_on} ({days_elapsed} day(s) ago) · scope: {data['scope']}")
    print("═" * 64)
    if after["messages"] == 0:
        print("  No usage recorded since the baseline yet. Come back after some work.")
        print("═" * 64)
        return 0

    rows = [
        ("tokens / message", "tok_per_msg", True, ""),
        ("output share %", "output_share_pct", True, ""),
        ("cache-read share %", "cache_read_share_pct", False, ""),
        ("frontier share %", "frontier_share_pct", True, ""),
    ]
    print(f"  {'metric':<22}{'before':>12}{'after':>12}   change")
    print("  " + "-" * 58)
    for label, key, lower_better, unit in rows:
        b, a = before[key], after[key]
        print(f"  {label:<22}{b:>12,}{a:>12,}   {delta_str(b, a, lower_better, unit)}")
    print("  " + "-" * 58)
    print(f"  sample: {before['messages']} msgs (before) vs {after['messages']} msgs (after)")
    print()
    print("  honest caveats:")
    print("  • workload changes move these numbers too — this is your real data,")
    print("    not a controlled experiment.")
    if after["messages"] < 20 or before["messages"] < 20:
        print("  • small sample on one side — treat deltas as noisy.")
    print()
    print("  share these aggregates with the community benchmark (opt-in only):")
    print("    python3 scripts/share_stats.py --help   ·   docs/telemetry.md")
    print("═" * 64)
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="alltoken baseline & progress")
    sub = ap.add_subparsers(dest="cmd", required=True)
    ps = sub.add_parser("save", help="snapshot the baseline")
    ps.add_argument("--root", default=".", help="project root")
    ps.add_argument("--force", action="store_true", help="overwrite existing baseline")
    ps.add_argument("--if-missing", action="store_true", help="no-op quietly if baseline exists")
    pr = sub.add_parser("report", help="compare now vs baseline")
    pr.add_argument("--root", default=".", help="project root")
    pr.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    if args.cmd == "save":
        return cmd_save(root, args.force, args.if_missing)
    return cmd_report(root, args.json)


if __name__ == "__main__":
    raise SystemExit(main())
