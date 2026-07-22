---
description: Audit this project for token waste (context floor, CLAUDE.md, MCPs, skills) and report a ranked, actionable plan.
argument-hint: "[--include-user]"
allowed-tools: Bash(python3:*), Read, Glob, Grep
---

You are running the **tokenwise audit**. Goal: find where this project silently
burns tokens on every Claude Code session, and report a ranked plan — without
changing anything.

## Steps

1. Run the deterministic audit engine:

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/audit.py" --root . $ARGUMENTS
   ```

   If `${CLAUDE_PLUGIN_ROOT}` is unset (running outside the plugin), use the
   `scripts/audit.py` path relative to this repo.

2. The script output is your ground truth for the mechanical findings
   (context floor, CLAUDE.md size, MCP count, skill descriptions). Do **not**
   re-estimate those numbers yourself — quote them.

3. Then add **judgment-level findings** the static script can't see. Skim the
   codebase and look for:
   - Repeated, deterministic work done by prompting that should be a script
     (formatting, renaming, boilerplate generation, data extraction).
   - Skills or agents that always use the frontier model for grunt work
     (candidates for a cheaper "minimum viable model").
   - Docs/examples embedded in CLAUDE.md that Claude could read on demand instead.

4. Present a single prioritized report:
   - Lead with the estimated context floor and addressable waste from the script.
   - List findings most-impactful first, each with a concrete one-line fix.
   - Separate **safe/automatic** fixes from ones that need a human decision.
   - End with: "Run `/token-optimize` to apply the safe fixes."

## Rules

- Be concise. This is a token-optimization tool; don't be hypocritical.
- Never invent savings percentages. Use the script's estimates and label them
  as estimates.
- Do not modify any files in this command — audit only.
