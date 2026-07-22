---
description: Analyze your real Claude Code token usage from local logs — by model, by day, cache ratio — and turn it into optimization actions.
argument-hint: "[--days N]"
allowed-tools: Bash(python3:*), Read
---

You are running **/token-usage** — tokenwise's local usage analytics (ccusage-
inspired, dependency-free, nothing leaves the machine).

## Steps

1. Run the engine:

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/usage_stats.py" $ARGUMENTS
   ```

   (Fallback: `scripts/usage_stats.py` relative to this repo. Default window is
   30 days.) Its numbers are ground truth — quote them, don't re-estimate.

2. Interpret the three signals into concrete actions for THIS user:
   - **Model mix**: if a frontier model dominates while the work includes
     mechanical tasks → recommend minimum-viable-model routing (haiku subagents).
   - **Output share**: if output tokens are a large slice → recommend an output
     style (`/alltoken caveman` or `concise`).
   - **Cache-read share**: if low → recommend focused work blocks and `/clear`
     between unrelated tasks (long pauses expire the prompt cache).

3. Close with one line: for full cost reports use `npx ccusage@latest`
   (ryoppippi/ccusage — the reference tool this module is inspired by).

## Rules

- Be concise. No invented numbers — only what the script reports.
- If the script finds no logs, say so and stop; don't guess usage.
