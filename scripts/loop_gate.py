#!/usr/bin/env python3
"""
alltoken loop-gate — the token killer for recurring/autonomous agents.

Loops (routines, cron agents, PR babysitters, "/loop" tasks) are the new
default way to use Claude Code — and the biggest token leak nobody optimizes:
every wakeup re-pays the full context just to discover, most of the time, that
NOTHING changed.

The gate fixes that deterministically: a zero-LLM fingerprint check that runs
BEFORE the model thinks. Unchanged → the loop ends the turn immediately, having
spent ~one cheap Bash call instead of a full reasoning pass. Changed → the loop
proceeds, and the gate tells it what moved.

It also records check history, so `suggest` can tell you the interval your loop
SHOULD be running at, based on how often the watched state actually changes —
ending the classic "poll every 5 minutes for something that changes twice a day".

State lives in <root>/.claude/alltoken/loops/<name>.json. No network, stdlib only.

Usage:
    loop_gate.py check   --name ci-watch [--watch GLOB ...] [--cmd "shell cmd"] [--root DIR]
    loop_gate.py suggest --name ci-watch [--root DIR]
    loop_gate.py list    [--root DIR]

Exit codes for `check`: 0 = CHANGED (or first run), 3 = UNCHANGED.
In a loop prompt:  gate says UNCHANGED → end the turn silently, no summary.
"""

from __future__ import annotations

import argparse
import glob as globmod
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

HISTORY_CAP = 500
SMALL_FILE = 1 << 20  # content-hash files up to 1 MB; bigger use size+mtime


def state_dir(root: Path) -> Path:
    return root / ".claude" / "alltoken" / "loops"


def state_path(root: Path, name: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "-" for c in name)
    return state_dir(root) / f"{safe}.json"


def fingerprint_watch(root: Path, patterns: list[str]) -> dict[str, str]:
    """Stable per-item digests for everything the patterns match."""
    items: dict[str, str] = {}
    for pat in patterns:
        for p in sorted(globmod.glob(str(root / pat), recursive=True)):
            path = Path(p)
            if not path.is_file():
                continue
            rel = str(path.relative_to(root)) if str(path).startswith(str(root)) else str(path)
            try:
                st = path.stat()
                if st.st_size <= SMALL_FILE:
                    h = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
                else:
                    h = f"big:{st.st_size}:{st.st_mtime_ns}"
            except OSError:
                h = "unreadable"
            items[rel] = h
    return items


def fingerprint_cmd(cmd: str) -> str:
    try:
        out = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=60
        )
        blob = f"{out.returncode}\n{out.stdout}\n{out.stderr}"
    except subprocess.TimeoutExpired:
        blob = "timeout"
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def load_state(sp: Path) -> dict:
    if sp.is_file():
        try:
            return json.loads(sp.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {}


def save_state(sp: Path, state: dict) -> None:
    sp.parent.mkdir(parents=True, exist_ok=True)
    sp.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- #
# check
# --------------------------------------------------------------------------- #
def cmd_check(root: Path, name: str, watch: list[str], cmd: str) -> int:
    sp = state_path(root, name)
    state = load_state(sp)

    files = fingerprint_watch(root, watch) if watch else {}
    cmd_fp = fingerprint_cmd(cmd) if cmd else ""
    now = int(time.time())

    prev_files = state.get("files", {})
    prev_cmd = state.get("cmd_fp", "")
    first_run = "files" not in state and "cmd_fp" not in state

    changed_paths = sorted(
        set(k for k in files if files[k] != prev_files.get(k))
        | set(k for k in prev_files if k not in files)
    )
    cmd_changed = bool(cmd) and cmd_fp != prev_cmd
    changed = first_run or bool(changed_paths) or cmd_changed

    hist = state.get("history", [])
    hist.append({"ts": now, "changed": changed})
    state.update({"files": files, "cmd_fp": cmd_fp, "watch": watch, "cmd": cmd,
                  "history": hist[-HISTORY_CAP:]})
    save_state(sp, state)

    if first_run:
        print(f"[loop-gate:{name}] INITIALIZED — baseline stored "
              f"({len(files)} file(s){', +cmd' if cmd else ''}). Proceed this run.")
        return 0
    if changed:
        what = []
        if changed_paths:
            shown = ", ".join(changed_paths[:5])
            more = f" (+{len(changed_paths) - 5} more)" if len(changed_paths) > 5 else ""
            what.append(f"files: {shown}{more}")
        if cmd_changed:
            what.append("command output changed")
        print(f"[loop-gate:{name}] CHANGED — {'; '.join(what)}. Proceed.")
        return 0

    streak = 0
    for h in reversed(hist):
        if h["changed"]:
            break
        streak += 1
    print(f"[loop-gate:{name}] UNCHANGED — {streak} consecutive quiet check(s). "
          f"End the turn now; no summary needed.")
    return 3


# --------------------------------------------------------------------------- #
# suggest
# --------------------------------------------------------------------------- #
def human_secs(s: float) -> str:
    if s >= 86400:
        return f"{s / 86400:.1f}d"
    if s >= 3600:
        return f"{s / 3600:.1f}h"
    if s >= 60:
        return f"{s / 60:.0f}m"
    return f"{s:.0f}s"


def cmd_suggest(root: Path, name: str) -> int:
    sp = state_path(root, name)
    state = load_state(sp)
    hist = state.get("history", [])
    if len(hist) < 5:
        print(f"[loop-gate:{name}] only {len(hist)} check(s) recorded — need ≥5 for a suggestion.")
        return 1

    checks = len(hist)
    changes = [h for h in hist if h["changed"]]
    change_ts = [h["ts"] for h in changes]
    rate = 100 * len(changes) / checks

    gaps = [b - a for a, b in zip(change_ts, change_ts[1:]) if b > a]
    check_gaps = [b["ts"] - a["ts"] for a, b in zip(hist, hist[1:]) if b["ts"] > a["ts"]]
    current = sorted(check_gaps)[len(check_gaps) // 2] if check_gaps else 0

    print(f"[loop-gate:{name}] {checks} checks · {len(changes)} changes ({rate:.0f}% hit rate)")
    if current:
        print(f"  current median check interval: ~{human_secs(current)}")
    if len(gaps) >= 2:
        med = sorted(gaps)[len(gaps) // 2]
        suggested = max(med // 2, 60)
        print(f"  median gap between real changes: ~{human_secs(med)}")
        print(f"  → suggested polling interval: ~{human_secs(suggested)} "
              f"(half the observed change gap)")
        if current and suggested > current * 2:
            saved = (1 - current / suggested) * 100
            print(f"  → at that interval you'd run ~{saved:.0f}% fewer wakeups "
                  f"for the same coverage.")
    else:
        print("  fewer than 2 observed changes — keep collecting before tuning the interval.")
    print("  honest note: derived from YOUR history; a change in workload resets the math.")
    return 0


def cmd_list(root: Path) -> int:
    d = state_dir(root)
    if not d.is_dir() or not any(d.glob("*.json")):
        print("no loop gates in this project yet — see /token-loop to set one up.")
        return 0
    for f in sorted(d.glob("*.json")):
        st = load_state(f)
        hist = st.get("history", [])
        changes = sum(1 for h in hist if h["changed"])
        print(f"  {f.stem}: {len(hist)} checks, {changes} changes, "
              f"watch={st.get('watch') or '—'} cmd={'yes' if st.get('cmd') else 'no'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="alltoken loop gate")
    sub = ap.add_subparsers(dest="op", required=True)
    pc = sub.add_parser("check")
    pc.add_argument("--name", required=True)
    pc.add_argument("--watch", action="append", default=[], help="glob (repeatable), relative to root")
    pc.add_argument("--cmd", default="", help="shell command whose output is fingerprinted")
    pc.add_argument("--root", default=".")
    ps = sub.add_parser("suggest")
    ps.add_argument("--name", required=True)
    ps.add_argument("--root", default=".")
    pl = sub.add_parser("list")
    pl.add_argument("--root", default=".")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    if args.op == "check":
        if not args.watch and not args.cmd:
            print("error: give at least one --watch glob or a --cmd", file=sys.stderr)
            return 2
        return cmd_check(root, args.name, args.watch, args.cmd)
    if args.op == "suggest":
        return cmd_suggest(root, args.name)
    return cmd_list(root)


if __name__ == "__main__":
    raise SystemExit(main())
