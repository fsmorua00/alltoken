---
name: minimum-viable-model
description: Use when deciding which Claude model a task, skill, or subagent should run on to save compute — routing grunt work (scraping, formatting, summarizing, extraction, boilerplate) to a cheaper model and reserving the frontier model for genuine judgment. Trigger when someone asks how to cut token/compute cost by model choice, or sets up a new skill/agent.
---

# Minimum viable model

The single biggest lever on compute cost is *which model does the work*. Compute
spent ≈ tokens processed × model tier. Most people leave the frontier model
selected for everything, including work a much cheaper model does perfectly.

## The rule of thumb

> If a task was solvable by AI a year ago, it does not need a frontier model.

Scraping, summarizing, formatting, fetching, renaming, extracting fields,
classifying, simple codegen from a template — all of this runs fine on a small,
cheap model. Reserve the frontier model for tasks needing real reasoning,
architecture, ambiguous tradeoffs, or subtle correctness.

## How to apply it

**In skills and subagents**, set the `model:` field in frontmatter to the
cheapest tier that reliably does the job:

```yaml
---
name: format-changelog
description: ...
model: haiku          # mechanical text shaping — no frontier model needed
---
```

Tiers, cheapest → most capable (current families):
- `haiku`  — mechanical, high-volume, low-ambiguity work.
- `sonnet` — general coding and analysis with moderate judgment.
- `opus` / frontier — architecture, hard debugging, ambiguous decisions.

**Fork the context when the subtask doesn't need history.** A grunt-work
subagent handed the whole conversation pays to re-read all of it. If it only
needs its immediate inputs, run it fresh so it starts from a clean, small context.

## Decision table

| Task shape | Model | Fork context? |
|---|---|---|
| Format / lint / rename / mechanical edit | haiku | yes |
| Summarize or extract from provided text | haiku | yes |
| Scrape / fetch / parse structured data | haiku | yes |
| Routine feature code in a known pattern | sonnet | usually |
| Cross-cutting refactor, ambiguous design | frontier | no |
| Hard bug, subtle correctness, security | frontier | no |

## Anti-patterns

- Using the frontier model "just to be safe" for repetitive mechanical work.
- Passing full conversation context to a subagent that only needs one file.
- Splitting a genuinely hard reasoning task onto a cheap model to save tokens —
  it will churn, retry, and cost *more*. Match the model to the work, both ways.
