#!/usr/bin/env python3
"""
alltoken SessionStart hook — one-line context-budget nudge.

Runs the deterministic audit and, ONLY if there is high-severity waste, injects
a single compact line of context so you're reminded to run `/token-audit`.
Deliberately silent when the project is already lean — a token-saving tool that
spams every session would defeat its own purpose.

Reads the Claude Code hook JSON on stdin, emits hookSpecificOutput.additionalContext.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    import audit  # local module
except Exception:
    # If the audit engine can't be imported, stay silent — never break a session.
    print(json.dumps({}))
    raise SystemExit(0)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        payload = {}

    root = Path(payload.get("cwd") or os.getcwd())
    try:
        report = audit.run(root, include_user=False)
    except Exception:
        print(json.dumps({}))
        return 0

    high = [f for f in report.findings if f.severity == "high"]
    if not high:
        # Nothing worth interrupting the session for.
        print(json.dumps({}))
        return 0

    floor = report.context_floor_tokens
    save = report.potential_savings_tokens
    line = (
        f"[alltoken] Context floor ~{floor:,} tok; ~{save:,} tok/session of "
        f"high-severity waste detected. Run /token-audit for details."
    )
    out = {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": line}}
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
