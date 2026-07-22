# Official Claude Code best practices — distilled

This is the distilled version of Anthropic's own guidance that `/alltoken`
enforces via the CLAUDE.md discipline block. Sources (read them — they're the
authority, this file is just the summary):

- Claude Code docs: https://docs.claude.com/en/docs/claude-code
- Engineering post "Claude Code: Best practices for agentic coding":
  https://www.anthropic.com/engineering/claude-code-best-practices

## Context (input tokens)

- **Keep CLAUDE.md short and human-readable.** It is loaded on every session;
  treat it as a directory of project conventions, not documentation. Rule of
  thumb: under ~200 lines. Long material belongs in files Claude reads on demand.
- **`/clear` between unrelated tasks.** Stale context costs tokens and degrades
  focus. **`/compact`** before the window fills when you must continue.
- **Work in focused blocks.** Prompt caching discounts repeated context, but the
  cache expires between long pauses — bursty, focused sessions are cheaper than
  trickled ones.
- **Audit what preloads.** MCP servers and skill descriptions load into every
  session. Disconnect servers you don't use; keep skill descriptions tight.
- **Read surgically.** Targeted searches and partial file reads beat whole-file
  dumps. Batch independent tool calls in parallel.

## Output (response tokens)

- **Ask for concision.** Response style is configurable (output styles / CLAUDE.md
  conventions). Concise responses cost less on every single turn.

## Model (compute per token)

- **Match the model to the task.** Lightweight, mechanical work (formatting,
  summarizing, extraction, scraping) runs fine on a small model like Haiku;
  reserve the frontier model for genuine judgment — architecture, hard debugging,
  ambiguous tradeoffs. Subagents accept a `model:` field for exactly this.
- **Fork context for grunt work.** A subagent that only needs its immediate
  inputs shouldn't inherit the whole conversation.

## Determinism (zero tokens)

- **Offload repeatable work to scripts, hooks, and skills.** Deterministic code
  costs no tokens, runs the same every time, and never hallucinates. Use AI for
  judgment; use scripts for everything repeatable.

## What this plugin does with all this

`/alltoken` turns the list above into an enforced, per-project reality:
the discipline block in CLAUDE.md makes every session load these rules; the
output style cuts response tokens; the `minimum-viable-model` skill and the
`token-auditor` agent (running on Haiku) put the model-routing advice into
practice; `compress_output.py` and the audit engine handle the deterministic
side. Nothing here is invented — it's the official guidance, operationalized.
