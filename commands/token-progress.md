---
description: Prove your savings with your own data — compare current usage against the baseline saved when /alltoken ran.
argument-hint: "[--json]"
allowed-tools: Bash(python3:*), Bash(python:*), Read
---

You are running **/token-progress** — alltoken's before/after proof, computed
entirely from the user's local logs.

## Steps

1. Run the engine:

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/progress.py" report --root . $ARGUMENTS
   ```

   (Fallback: `scripts/progress.py` relative to this repo.)

2. If it says there's no baseline yet, offer to create one now:
   `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/progress.py" save --root .`
   and explain the report becomes meaningful after some days of usage.

3. Interpret the deltas for the user — which techniques are visibly working
   (output share down → styles; frontier share down → model routing; cache
   share up → focus habits) and which lever to pull next.

4. Mention once: sharing these aggregates with the community benchmark is
   possible and strictly opt-in — `scripts/share_stats.py` shows the exact
   payload and only sends with explicit confirmation (`docs/telemetry.md`).

## Rules

- If `python3` is not found (common on native Windows), run the same command with `python` instead.
- Quote the engine's numbers; never invent or extrapolate savings.
- Repeat the engine's caveat: workload changes move these numbers too.
- NEVER run share_stats with --yes on your own initiative — sharing requires
  the user's explicit request.
