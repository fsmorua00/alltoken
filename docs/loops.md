# Loop discipline — token optimization for recurring agents

Autonomous loops are the new default: routines, cron-fired agents, PR
babysitters, deploy watchers, `/loop` tasks. They're also the biggest token
leak in modern Claude Code usage, because loop waste MULTIPLIES: whatever a
single wakeup wastes, the schedule pays it 24-100×/day.

## The six loop leaks (and the fix for each)

| # | Leak | Fix |
|---|---|---|
| 1 | **The no-op wakeup** — full context + reasoning to conclude "nothing changed" | `loop_gate.py check` runs BEFORE the model thinks; UNCHANGED → end turn in ~one Bash call |
| 2 | **Interval mismatch** — polling every 5 min for something that changes twice a day | `loop_gate.py suggest` derives the real change cadence from YOUR history and recommends the interval |
| 3 | **Context floor × N** — the preloaded context (CLAUDE.md, MCPs, skills) is re-paid on every wakeup | `/token-audit`'s floor matters N× more in loops; trim it first |
| 4 | **State re-derived each run** — the loop re-scans the world to rebuild what it already knew | Persist a compact state file between runs (the gate does this for change state; do the same for task state) |
| 5 | **No-op narration** — "Still watching, nothing to report 👍" every 10 minutes | Discipline rule: quiet wakeups are SILENT. Summaries only on change or completion |
| 6 | **Frontier model on watch duty** — the check turn needs no reasoning | The gate removes most check turns entirely; for the rest, minimum-viable-model applies |

## The seventh leak: batch work over N items

The worst tangle of all: "analyze these 100 lawsuits, one per session/wakeup."
Without external state the agent re-derives progress by reasoning ("which ones
did I do?"), re-analyzes finished items, and carries every previous result in
context until it drowns in its own history.

Fix: `work_queue.py` — a crash-safe, file-based queue that IS the progress:

```
wakeup
  └─ work_queue.py next --name cases
       ├─ ALL DONE (exit 3) → report → final summary → STOP the loop
       ├─ in-progress elsewhere (exit 4) → end turn silently
       └─ CLAIMED i042 "Processo 0001234-56"
            └─ process ONLY i042 → write results/cases/i042.md
               → work_queue.py done --id i042 --note "risco alto; ver arquivo"
               → arm next wakeup → end turn
```

Properties: atomic writes (tmp+rename), stale-claim reclaim after a timeout
(a crashed iteration's item returns to the pool), fail/retry with a max-attempt
cap, `status` with ETA from real pace, `report` as the final index. Context
stays one-item-small whether N is 10 or 10,000. Set up with `/token-batch`.

## The core pattern (watch-style loops)

```
wakeup
  └─ loop_gate.py check --name X --watch ... --cmd ...     (deterministic, ~0 tok)
       ├─ UNCHANGED → end turn. Silent. Done.
       └─ CHANGED (says what moved)
            └─ read ONLY what moved → act → update state file → concise report
```

## Honest math

For a loop firing F times/day where the watched state changes C times/day, the
gate eliminates the reasoning cost of (F − C) wakeups. Whether that's 50% or
95% depends on your F and C — which is exactly what `suggest` measures from
your own gate history. We don't invent the number; your loop's history is the
number.

## Prior art — and the gap this fills (researched July 2026)

The pain is documented at the source: Anthropic's own engineering writing on
[long-running agent harnesses](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
describes agents that "try to do too much at once", run out of context
mid-work, leaving the next session "to guess at what happened". Community
reports match: A-B-A failure loops (retrying an approach the agent forgot it
already failed), permanent information loss on every `/compact`, and duplicate
work are among the most-reported Claude Code issues.

What exists, and what it doesn't cover:

- **Ralph Wiggum** (official plugin) — re-injects the same prompt in a
  while-true loop; filesystem/git as state. No per-item ledger, no claim
  semantics.
- **[Claude-Autopilot](https://github.com/benbasha/Claude-Autopilot)** (~240⭐)
  — queues *prompts* in VS Code with auto-resume; not item-level work state.
- **[task-orchestrator](https://github.com/jpicklyk/task-orchestrator)** (~200⭐),
  [taskqueue-mcp](https://github.com/chriscarrollsmith/taskqueue-mcp),
  [agent-task-queue](https://github.com/block/agent-task-queue) — MCP-server
  task systems; heavyweight, need a running host, aimed at dev workflows.

As far as our research found, **no existing tool combines**: a file-based
per-item queue + claim-one-at-a-time + stale-claim reclaim (crashed iteration's
item returns to the pool) + results-to-files convention + compatibility with
scheduled-wakeup loops where nothing stays running between iterations. That
combination is exactly `work_queue.py`. One pattern we adopted straight from
Anthropic's harness write-up: state lives in JSON deliberately — models are
less likely to inappropriately rewrite JSON than Markdown.

## What the gate is NOT

- Not a scheduler — it doesn't fire your loop; it makes each firing cheap.
- Not magic for genuinely-changing state — if every wakeup finds changes, the
  gate adds one cheap check and saves nothing (and `suggest` will tell you so).
- Not a watcher of things it can't see — `--cmd` must surface the external
  state (CI status, remote HEAD) as text; if no cheap read-only command
  exists, the gate can't help with that part.
