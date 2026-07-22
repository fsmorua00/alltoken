---
description: Apply the safe, high-confidence token optimizations to this project (with confirmation before each change).
argument-hint: "[--yes]"
allowed-tools: Bash(python3:*), Bash(python:*), Read, Edit, Write, Glob, Grep
---

You are running **alltoken optimize**. Goal: actually apply the safe wins the
audit surfaces. Every change must be reversible via git and shown to the user.

## Steps

1. First run the audit to get current state:

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/audit.py" --root . --json
   ```

2. Work through the **safe** optimizations only. For each, show the exact diff
   before applying, and apply it unless the user passed `--yes`:

   a. **Concise output** — if no concise-output convention exists, add a short
      block to `CLAUDE.md` (create it if missing):
      > ## Response style
      > Be concise. Answer directly; skip preamble and restating the question.
      > Prefer bullet points and code over prose. Don't narrate routine steps.

   b. **CLAUDE.md trim** — if CLAUDE.md is over the 200-line guideline, propose
      a lean rewrite: keep project-specific conventions, move long docs/examples
      to separate files referenced by path. Show the before/after size. Never
      delete information silently — relocate it and say where it went.

   c. **Skill descriptions** — for any skill flagged with a bloated description,
      tighten it to the trigger conditions only. Show the diff.

   d. **Minimum-viable-model hints** — for skills/agents doing mechanical work
      on the frontier model, add a `model:` hint for a cheaper tier where the
      skill/agent format supports it. Explain the tradeoff per change.

3. **Do NOT** touch anything requiring a human architectural decision
   (disconnecting an MCP the user may rely on, converting a prompt-driven flow
   into a script). Instead, list those as "recommended, needs your call."

## Rules

- If `python3` is not found (common on native Windows), run the same command with `python` instead — the scripts are pure stdlib and OS-independent.
- Show every change as a diff before writing. Batch related edits.
- Never fabricate savings numbers.
- After applying, print a short summary: what changed, and re-run the audit to
  show the new estimated context floor.
- Remind the user the changes are staged in git and easy to revert.
