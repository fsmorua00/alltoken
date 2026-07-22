---
description: Make a recurring/autonomous loop token-efficient — set up a deterministic change-gate so quiet wakeups cost ~zero tokens.
argument-hint: "[name of the recurring task]"
allowed-tools: Bash(python3:*), Bash(python:*), Read, Edit, Write, Glob, Grep
---

You are running **/token-loop** — alltoken's loop discipline. Loops (routines,
cron agents, PR watchers, /loop tasks) re-pay full context on EVERY wakeup,
usually just to discover nothing changed. The gate makes quiet wakeups nearly
free.

## Steps

1. Identify the recurring task: from `$ARGUMENTS` or by asking ONE short
   question. Determine what state it actually reacts to:
   - files/dirs in the repo → `--watch` globs
   - external state (CI, PR, queue, API) → a cheap read-only `--cmd` whose
     output changes when the state does (e.g. `git ls-remote origin main`,
     a status CLI call)

2. Pick a short gate name and initialize it:

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/loop_gate.py" check --name <name> [--watch <glob> ...] [--cmd "<cmd>"]
   ```

   First run prints INITIALIZED and stores the baseline.

3. Install the discipline into the loop itself — add this to the loop's prompt,
   skill, or routine definition (adapt paths):

   > FIRST, before any reading or reasoning, run:
   > `python3 <plugin>/scripts/loop_gate.py check --name <name> [--watch ...] [--cmd ...]`
   > If it prints UNCHANGED: end the turn immediately. No summary, no
   > re-reading, no "still watching" message.
   > If CHANGED: it tells you what moved — start from that, read only what's
   > needed.

4. Tell the user about interval tuning: after ~a day of checks,

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/loop_gate.py" suggest --name <name>
   ```

   reports the observed change cadence and the polling interval the loop
   should actually use (often several times longer than the configured one —
   that's wakeups eliminated entirely).

## Why this saves real tokens

A wakeup that passes through the gate on UNCHANGED costs one Bash call.
A wakeup without the gate costs the full context reload + a reasoning pass +
usually a pointless summary. For a loop that fires 100×/day and changes
5×/day, ~95% of its reasoning cost is waste the gate removes. (Your numbers
will differ — `suggest` computes them from your own history.)

## Rules

- If `python3` is not found (common on native Windows), use `python` instead.
- The gate's `--cmd` must be cheap and read-only (status checks, ls-remote) —
  never a mutating command.
- Never claim savings percentages beyond what `suggest` derives from the
  user's own history.
