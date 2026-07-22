---
description: Show the alltoken toolbox — every token-saving tool in this plugin and how to use it.
allowed-tools: Bash(python3:*), Bash(python:*), Read
---

Present the **alltoken toolbox** to the user: a single plugin aggregating the
best Claude Code token-saving techniques. Keep it short and scannable.

If helpful, run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/audit.py" --root . ` to
show the current project's context floor alongside the menu.

Show this menu (adapt to what the user asks):

## alltoken toolbox

**One-shot magic**
- `/alltoken [caveman|telegraphic|concise]` — apply EVERYTHING at once: audit,
  output styles installed + activated, and the official best-practices block
  injected into CLAUDE.md so every session enforces them.

**Audit & optimize (proven, safe)**
- `/token-audit` — measure the context floor and rank token waste.
- `/token-optimize` — apply the safe fixes (concise output, trim CLAUDE.md, tighten skills).

**Output modes (cut OUTPUT tokens)** — install then activate:
- `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/install_styles.py` then `/output-style caveman`
- Styles: **Caveman** (grunt-terse), **Telegraphic** (clipped), **Concise** (professional).
- Reset anytime with `/output-style default`. Code/commands stay exact in every mode.

**Model routing (cut COMPUTE)**
- Skill `minimum-viable-model` — route grunt work to Haiku, keep frontier for judgment.
- Subagent `token-auditor` — reviews project logic for waste (runs on Haiku).

**Loop mode (recurring/autonomous agents)**
- `/token-loop` — deterministic change-gate: quiet wakeups end in ~zero tokens;
  `loop_gate.py suggest` tunes the polling interval from YOUR history.
  Patterns: `docs/loops.md`.

**Input compression**
- `some-noisy-cmd 2>&1 | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/compress_output.py --stats`

**Measure reality**
- `/token-usage` — where your tokens actually went (last 30 days, local logs,
  by model / output share / cache ratio).
- `/token-progress` — before/after proof vs the baseline `/alltoken` saved,
  from your own logs. Optional opt-in sharing to the community benchmark
  (`docs/telemetry.md`).
- Ecosystem radar: `docs/ecosystem.md` — the top-starred tools analyzed, what we
  absorbed and what to install as companions (Serena, ccusage, router).

**Experimental (opt-in, tradeoffs — read the docs first)**
- Text-as-image: `scripts/text_to_image.py` (lossy; never for code).
- Engine swap to other providers: `docs/engine-swap.md`.

End by asking which one the user wants to run or set up. Be concise.

Note: if `python3` is missing (common on native Windows), use `python` instead.
