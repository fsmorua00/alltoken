---
description: One-shot magic — apply ALL proven token-saving techniques + official Claude Code best practices to this project at once.
argument-hint: "[caveman|telegraphic|concise] [--shared] [--yes]"
allowed-tools: Bash(python3:*), Read, Edit, Write, Glob, Grep
---

You are running **/alltoken** — alltoken's one-shot setup. Goal: in a single
command, this project gets every proven token-saving technique AND a persistent
block of Anthropic's official best practices that every future session loads.

## Steps

1. Parse `$ARGUMENTS`:
   - optional style: `caveman`, `telegraphic`, or `concise` (default: `concise`)
   - optional `--shared` (activate style team-wide in settings.json instead of
     settings.local.json)
   - optional `--yes` (skip confirmation on the CLAUDE.md trim step)

2. Run the deterministic engine:

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/apply_all.py" --root . --style <style> [--shared]
   ```

   (If `${CLAUDE_PLUGIN_ROOT}` is unset, use `scripts/apply_all.py` relative to
   this repo.) Its summary is ground truth — quote its numbers, don't re-estimate.

   The engine, deterministically and idempotently:
   - audits the context floor (before/after)
   - installs the Caveman/Telegraphic/Concise output styles into the project
   - activates the chosen style via the `outputStyle` settings key
   - injects/updates the marked "token discipline" block in CLAUDE.md encoding
     the official best practices (concision, context hygiene, minimum-viable-model
     routing, scripts-over-reprompting)

3. Judgment layer (yours):
   a. If the post-audit still flags CLAUDE.md over the ~200-line guideline,
      propose a lean rewrite: keep project conventions, relocate long docs to
      files read on demand, and say where every piece of content went. Show the
      diff; apply directly if `--yes` was passed, otherwise ask one short
      confirmation. Never delete or relocate user content silently.
   b. List the engine's "needs your call" items verbatim (e.g. disconnecting
      MCP servers) — do NOT act on them.

4. Measure reality: if `~/.claude/projects` exists, also run

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/usage_stats.py" --days 30
   ```

   and fold its top signal (model mix / output share / cache ratio) into the
   report. If it finds no logs, skip silently.

5. Final report, short:
   - context floor before → after
   - active output style and how to revert (`/output-style default`)
   - note that the CLAUDE.md block now enforces the official best practices on
     every session in this project
   - all file changes are visible in `git diff`
   - close with at most TWO ecosystem recommendations from
     `${CLAUDE_PLUGIN_ROOT}/docs/ecosystem.md`, picked for THIS project
     (e.g. Serena for large codebases; ccusage for full cost reports) — one
     line each, links included.

## Rules

- Be concise — this is a token-saving tool.
- Never invent savings numbers; quote the engine's estimates, labelled as estimates.
- Mechanical steps are automatic; anything touching user-authored content shows
  a diff first.
- For the official guidance itself, see `${CLAUDE_PLUGIN_ROOT}/docs/official-best-practices.md`.
