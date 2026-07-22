#!/usr/bin/env python3
"""
alltoken share — OPT-IN: send your before/after AGGREGATES to the community
benchmark, so "one command saves tokens" becomes a measured public number
instead of a claim.

Consent flow, non-negotiable:
  1. Builds the payload from your local progress report (aggregate numbers only:
     tokens/message, output share, cache-read share, frontier share, counts).
  2. PRINTS the exact payload.
  3. Sends ONLY with --yes (after you've seen what leaves the machine).

Never collected, never sent: code, prompts, file contents, file paths, project
names, hostnames, usernames. The anon id is a random UUID stored locally.
Full policy: docs/telemetry.md. Server source: server/ (self-hostable, MIT).

Usage:
    python share_stats.py [--root DIR] [--endpoint URL] [--yes]

Endpoint resolution: --endpoint flag, else $ALLTOKEN_ENDPOINT. There is no
hardcoded default — sharing is impossible unless you point it somewhere.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import progress  # noqa: E402  (local module)

try:
    PLUGIN_VERSION = json.loads(
        (HERE.parent / ".claude-plugin" / "plugin.json").read_text()
    ).get("version", "unknown")
except (OSError, json.JSONDecodeError):
    PLUGIN_VERSION = "unknown"


def anon_id() -> str:
    p = Path.home() / ".claude" / "alltoken" / "anon_id"
    if p.is_file():
        val = p.read_text().strip()
        if val:
            return val[:64]
    val = str(uuid.uuid4())
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(val + "\n")
    return val


def build_payload(root: Path) -> dict | None:
    bp = progress.baseline_path(root)
    if not bp.is_file():
        print("No baseline for this project — run `progress.py save` (or /alltoken) first.", file=sys.stderr)
        return None
    base = json.loads(bp.read_text(encoding="utf-8"))
    from datetime import date, timedelta

    saved_on = base["saved_on"]
    since = (date.fromisoformat(saved_on) + timedelta(days=1)).isoformat()
    data = progress.project_usage(root, days=0, since=since)
    if data is None:
        print("No Claude Code logs found on this machine.", file=sys.stderr)
        return None
    after = progress.metrics_from(data)
    if after["messages"] == 0:
        print("No usage since the baseline yet — nothing meaningful to share.", file=sys.stderr)
        return None
    return {
        "schema": 1,
        "anon_id": anon_id(),
        "plugin_version": PLUGIN_VERSION,
        "days_since_baseline": (date.today() - date.fromisoformat(saved_on)).days,
        "before": base["metrics"],
        "after": after,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="alltoken opt-in benchmark sharing")
    ap.add_argument("--root", default=".", help="project root")
    ap.add_argument("--endpoint", default=os.environ.get("ALLTOKEN_ENDPOINT", ""), help="benchmark server URL")
    ap.add_argument("--yes", action="store_true", help="confirm sending AFTER reviewing the payload")
    args = ap.parse_args(argv)

    payload = build_payload(Path(args.root).resolve())
    if payload is None:
        return 1

    print("This — and ONLY this — would be sent:")
    print(json.dumps(payload, indent=2))
    print()

    if not args.endpoint:
        print(
            "No endpoint configured (set --endpoint or $ALLTOKEN_ENDPOINT).\n"
            "Nothing was sent. The community server address is announced in the "
            "repo README once live; you can also self-host it (server/).",
        )
        return 0

    if not args.yes:
        print(f"Endpoint: {args.endpoint}\nNothing sent. Re-run with --yes to confirm.")
        return 0

    req = urllib.request.Request(
        args.endpoint.rstrip("/") + "/v1/report",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode()
        print(f"sent ✓ server replied: {body}")
        return 0
    except urllib.error.URLError as e:
        print(f"send failed: {e}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
