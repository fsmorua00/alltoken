# Ecosystem radar — the top-starred Claude Code projects, analyzed

tokenwise's job is to aggregate the best token-saving techniques into one
plugin. Some of the best ideas live in other open-source projects. This is the
honest map: what we **absorbed** (re-implemented, dependency-free), what we
**recommend as companions** (better used directly), and what each one does for
your tokens. Star counts are approximate as of July 2026 — check the repos.

## Absorbed into tokenwise

| Project | ⭐ | Idea | Where it lives here |
|---|---|---|---|
| [ccusage](https://github.com/ryoppippi/ccusage) | ~16k | Parse Claude Code's local JSONL logs to see where tokens actually go | `/token-usage` · `scripts/usage_stats.py` (minimal, dependency-free subset; use ccusage itself for cost reports and dashboards) |
| [SuperClaude](https://github.com/SuperClaude-Org/SuperClaude_Framework) | ~23k | "Token-efficiency mode" — compressed communication styles | Our output styles: Caveman / Telegraphic / Concise (`/alltoken caveman`) |
| Caveman-style plugins | — | Make Claude answer in grunt-short prose | `output-styles/caveman.md` — ours keeps code/commands/numbers exact |

## Recommended companions (install them directly — we don't wrap them)

| Project | ⭐ | What it does for tokens | When to add it |
|---|---|---|---|
| [Serena](https://github.com/oraios/serena) | ~19k | LSP-based semantic retrieval: Claude reads *symbols*, not whole files — big INPUT-token saver | Medium/large codebases where whole-file reads dominate |
| [ccusage](https://github.com/ryoppippi/ccusage) | ~16k | Full cost reports, live dashboards, multi-agent usage | When `/token-usage` isn't enough |
| [claude-code-router](https://github.com/musistudio/claude-code-router) | large | Local gateway that routes requests across providers/models — the concrete implementation of our `docs/engine-swap.md` | Only after in-ecosystem MVM routing isn't enough; same quality/privacy caveats |
| [awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code) | large | Curated discovery hub for the whole ecosystem | Finding anything not covered here |

## Analyzed and deliberately NOT absorbed

- **Full frameworks (SuperClaude, Claude-Flow, BMAD and friends)** — powerful,
  but they load their own commands/personas/context into every session, which is
  itself a token cost. tokenwise stays minimal on purpose: our whole surface is
  a handful of commands and one ~200-token CLAUDE.md block.
- **Big subagent packs (e.g. wshobson/agents, 80+ agents)** — great catalog, and
  their per-agent model tiers (haiku/sonnet/opus) validate our minimum-viable-model
  approach. But installing dozens of agents you don't use pays context rent every
  session. Cherry-pick the 2–3 you need instead.
- **MCP multiplexers / context compressors with big claims (90%+)** — promising
  direction, but measure on your own workload before believing any percentage.
  (That skepticism applies to us too: our numbers are labelled estimates.)

## The principle

Prefer the smallest tool that produces the saving. A technique that costs
context to *have installed* must save more than it costs — that's the bar every
tokenwise feature has to clear, and the bar we recommend you apply to everything
in this list.
