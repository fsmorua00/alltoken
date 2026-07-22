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

## The core pattern

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

## What the gate is NOT

- Not a scheduler — it doesn't fire your loop; it makes each firing cheap.
- Not magic for genuinely-changing state — if every wakeup finds changes, the
  gate adds one cheap check and saves nothing (and `suggest` will tell you so).
- Not a watcher of things it can't see — `--cmd` must surface the external
  state (CI status, remote HEAD) as text; if no cheap read-only command
  exists, the gate can't help with that part.
