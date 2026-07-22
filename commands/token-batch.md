---
description: Process N items across loop iterations WITHOUT getting tangled — crash-safe work queue: claim one, do one, mark done, end turn.
argument-hint: "[what to process, e.g. 'analyze the 100 lawsuits in cases/']"
allowed-tools: Bash(python3:*), Bash(python:*), Read, Edit, Write, Glob, Grep
---

You are running **/token-batch** — alltoken's batch discipline. The pain it
kills: an agent looping over N items (lawsuits, documents, tickets, repos)
loses track, re-analyzes finished items, and drags every previous result
through the context until it drowns. The queue file is the ONLY memory of
progress — the agent never re-derives it by reasoning.

## Setup (once)

1. From `$ARGUMENTS` (or one short question), determine the item list:
   - a file with one item per line → `--items-from list.txt`
   - files on disk → `--glob "cases/*.pdf"`
   - explicit → repeated `--item "..."`

2. Create the queue and a results directory:

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/work_queue.py" init --name <name> --items-from <file>
   mkdir -p results/<name>
   ```

3. Install the iteration contract into the loop's prompt/routine (adapt paths):

   > Each wakeup, run EXACTLY this sequence:
   > 1. `work_queue.py next --name <name>`
   >    - exit 3 (ALL DONE) → run `report`, deliver the final summary, STOP the loop.
   >    - exit 4 (in progress elsewhere) → end the turn silently.
   > 2. Idempotency check: if `results/<name>/<id>.md` ALREADY exists, verify
   >    it looks complete and jump to step 5 — never redo finished work.
   > 3. Process ONLY the claimed item. Do NOT read other items' results, do NOT
   >    summarize past progress — the queue already knows it.
   > 4. Write the item's result to `results/<name>/<id>.md`.
   > 5. `work_queue.py done --name <name> --id <id> --note "1 line + result path"`
   >    (on unrecoverable error: `fail --id <id> --note "why"` — it retries up
   >    to --max-attempts, then parks as failed)
   > 6. End the turn. One item per wakeup. No narration between items.

## Why this saves tokens AND sanity

- Progress lives in a file, not in reasoning → zero tokens re-deriving "where
  was I?", zero duplicated analyses.
- Each turn touches ONE item → context stays small forever, no matter if N is
  10 or 10,000.
- Crash-safe: an iteration that dies mid-item is reclaimed automatically after
  the claim timeout. Idempotent by construction.
- `status` gives real progress + ETA from actual pace; `report` is the final
  deliverable index.

## Rules

- If `python3` is not found (common on native Windows), use `python` instead.
- Never process an item without claiming it via `next`; never mark `done`
  without a result file written.
- Results in files, one-line notes in the queue — long content NEVER goes into
  the conversation.
- Combine with `/token-loop`'s gate when the batch also watches external state.
