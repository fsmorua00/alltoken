#!/usr/bin/env python3
"""
alltoken work-queue — deterministic memory for batch loops.

THE pain it kills: an agent must process N items across loop iterations
(example: analyze 100 lawsuits, one wakeup per case). Without external state
it "gets tangled": re-derives progress by reasoning, re-analyzes finished
items, drags every previous result through the context, and drowns. The fix
is boring and bulletproof: a crash-safe, file-based queue that IS the truth
about progress — the agent never has to remember anything between turns.

Per-iteration contract (the whole discipline):
    next  → claims exactly ONE pending item (atomic, stale-claim reclaim)
    ...the turn processes ONLY that item, writes its result to a file...
    done  → marks it complete with a one-line note
    → pending remain? arm the next wakeup and END the turn (small, silent)
    → queue empty? print the final report and STOP the loop.

State: <root>/.claude/alltoken/queues/<name>.json (atomic tmp+rename writes).
Results belong in files (--note points at them), never in conversation memory.
Zero dependencies, no network.

Usage:
    work_queue.py init   --name cases --items-from list.txt | --item "..." (rep.) | --glob "docs/*.pdf"
    work_queue.py next   --name cases [--claim-timeout 3600]
    work_queue.py done   --name cases --id i007 [--note "1-line result or path"]
    work_queue.py fail   --name cases --id i007 [--note "why"] [--max-attempts 3]
    work_queue.py status --name cases
    work_queue.py report --name cases

Exit codes for `next`: 0 item claimed · 3 ALL DONE · 4 nothing pending but
items still in progress (another worker holds them; wait, don't reprocess).
"""

from __future__ import annotations

import argparse
import glob as globmod
import json
import os
import sys
import time
from pathlib import Path

DEFAULT_CLAIM_TIMEOUT = 3600  # seconds before an in_progress claim is stale


def queue_path(root: Path, name: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "-" for c in name)
    return root / ".claude" / "alltoken" / "queues" / f"{safe}.json"


def load(qp: Path) -> dict:
    if not qp.is_file():
        print(f"error: queue not found at {qp} — run `init` first.", file=sys.stderr)
        raise SystemExit(2)
    return json.loads(qp.read_text(encoding="utf-8"))


def save(qp: Path, q: dict) -> None:
    qp.parent.mkdir(parents=True, exist_ok=True)
    tmp = qp.with_suffix(".tmp")
    tmp.write_text(json.dumps(q, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, qp)  # atomic on POSIX and Windows


def counts(q: dict) -> dict:
    c = {"pending": 0, "in_progress": 0, "done": 0, "failed": 0}
    for it in q["items"]:
        c[it["status"]] += 1
    return c


# --------------------------------------------------------------------------- #
# init
# --------------------------------------------------------------------------- #
def cmd_init(root: Path, name: str, items_from: str, items: list[str], glob_pat: str, force: bool) -> int:
    qp = queue_path(root, name)
    if qp.is_file() and not force:
        print(f"error: queue '{name}' already exists ({qp}). Use --force to recreate "
              f"(existing progress will be LOST).", file=sys.stderr)
        return 1

    texts: list[str] = []
    if items_from:
        src = Path(items_from)
        if not src.is_file():
            print(f"error: {src} not found", file=sys.stderr)
            return 2
        texts += [l.strip() for l in src.read_text(encoding="utf-8").splitlines() if l.strip()]
    texts += [i.strip() for i in items if i.strip()]
    if glob_pat:
        texts += sorted(str(Path(p)) for p in globmod.glob(str(root / glob_pat), recursive=True))
    # de-dup preserving order
    seen: set[str] = set()
    texts = [t for t in texts if not (t in seen or seen.add(t))]
    if not texts:
        print("error: no items (use --items-from, --item, or --glob)", file=sys.stderr)
        return 2

    q = {
        "schema": 1,
        "name": name,
        "created": int(time.time()),
        "items": [
            {"id": f"i{n:03d}", "item": t, "status": "pending", "attempts": 0,
             "claimed_at": 0, "finished_at": 0, "note": ""}
            for n, t in enumerate(texts, 1)
        ],
    }
    save(qp, q)
    print(f"queue '{name}' created: {len(texts)} item(s) → {qp}")
    print("each loop iteration: `next` → process ONLY that item → `done` → end turn.")
    return 0


# --------------------------------------------------------------------------- #
# next
# --------------------------------------------------------------------------- #
def cmd_next(root: Path, name: str, claim_timeout: int) -> int:
    qp = queue_path(root, name)
    q = load(qp)
    now = int(time.time())

    # reclaim stale claims (crashed/abandoned turns)
    reclaimed = 0
    for it in q["items"]:
        if it["status"] == "in_progress" and now - it["claimed_at"] > claim_timeout:
            it["status"] = "pending"
            it["claimed_at"] = 0
            reclaimed += 1

    c = counts(q)
    if c["pending"] == 0:
        save(qp, q)
        if c["in_progress"] > 0:
            print(f"[queue:{name}] nothing pending, {c['in_progress']} still in progress "
                  f"elsewhere — WAIT, do not reprocess. End the turn.")
            return 4
        print(f"[queue:{name}] ALL DONE — {c['done']} done, {c['failed']} failed. "
              f"Run `report` for the final summary, then STOP the loop.")
        return 3

    item = next(it for it in q["items"] if it["status"] == "pending")
    item["status"] = "in_progress"
    item["claimed_at"] = now
    item["attempts"] += 1
    save(qp, q)

    total = len(q["items"])
    done_n = c["done"]
    note = f" (reclaimed {reclaimed} stale)" if reclaimed else ""
    print(f"[queue:{name}] CLAIMED {item['id']} — progress {done_n}/{total}{note}")
    print(f"  item: {item['item']}")
    print(f"  process ONLY this item. Then: work_queue.py done --name {name} --id {item['id']} --note \"...\"")
    return 0


# --------------------------------------------------------------------------- #
# done / fail
# --------------------------------------------------------------------------- #
def _find(q: dict, item_id: str) -> dict | None:
    return next((it for it in q["items"] if it["id"] == item_id), None)


def cmd_done(root: Path, name: str, item_id: str, note: str) -> int:
    qp = queue_path(root, name)
    q = load(qp)
    it = _find(q, item_id)
    if it is None:
        print(f"error: no item '{item_id}' in queue '{name}'", file=sys.stderr)
        return 2
    it["status"] = "done"
    it["finished_at"] = int(time.time())
    it["note"] = note[:500]
    save(qp, q)
    c = counts(q)
    total = len(q["items"])
    if c["pending"] + c["in_progress"] == 0:
        tail = "Queue EMPTY — run report and stop the loop."
    else:
        tail = f"{c['pending']} pending — arm next wakeup and end the turn."
    print(f"[queue:{name}] {item_id} done ({c['done']}/{total}). {tail}")
    return 0


def cmd_fail(root: Path, name: str, item_id: str, note: str, max_attempts: int) -> int:
    qp = queue_path(root, name)
    q = load(qp)
    it = _find(q, item_id)
    if it is None:
        print(f"error: no item '{item_id}' in queue '{name}'", file=sys.stderr)
        return 2
    it["note"] = note[:500]
    if it["attempts"] >= max_attempts:
        it["status"] = "failed"
        it["finished_at"] = int(time.time())
        print(f"[queue:{name}] {item_id} FAILED permanently after {it['attempts']} attempt(s).")
    else:
        it["status"] = "pending"
        it["claimed_at"] = 0
        print(f"[queue:{name}] {item_id} failed (attempt {it['attempts']}/{max_attempts}) — requeued.")
    save(qp, q)
    return 0


# --------------------------------------------------------------------------- #
# status / report
# --------------------------------------------------------------------------- #
def cmd_status(root: Path, name: str) -> int:
    q = load(queue_path(root, name))
    c = counts(q)
    total = len(q["items"])
    done_ts = sorted(it["finished_at"] for it in q["items"] if it["status"] == "done" and it["finished_at"])
    line = f"[queue:{name}] {c['done']}/{total} done · {c['pending']} pending · " \
           f"{c['in_progress']} in progress · {c['failed']} failed"
    if len(done_ts) >= 3 and c["pending"]:
        pace = (done_ts[-1] - done_ts[0]) / max(1, len(done_ts) - 1)
        eta = pace * c["pending"]
        unit = f"~{eta/3600:.1f}h" if eta >= 3600 else f"~{eta/60:.0f}m"
        line += f" · ETA {unit} at current pace"
    print(line)
    return 0


def cmd_report(root: Path, name: str) -> int:
    q = load(queue_path(root, name))
    c = counts(q)
    print(f"═══ queue '{name}' final report — {c['done']} done, {c['failed']} failed, "
          f"{c['pending'] + c['in_progress']} unfinished ═══")
    for it in q["items"]:
        mark = {"done": "✔", "failed": "✘", "pending": "·", "in_progress": "…"}[it["status"]]
        note = f" — {it['note']}" if it["note"] else ""
        print(f"  {mark} {it['id']} {it['item'][:70]}{note}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="alltoken batch work-queue")
    sub = ap.add_subparsers(dest="op", required=True)

    pi = sub.add_parser("init")
    pi.add_argument("--name", required=True)
    pi.add_argument("--items-from", default="", help="file with one item per line")
    pi.add_argument("--item", action="append", default=[], help="inline item (repeatable)")
    pi.add_argument("--glob", default="", help="glob relative to root; each match is an item")
    pi.add_argument("--force", action="store_true")
    pi.add_argument("--root", default=".")

    pn = sub.add_parser("next")
    pn.add_argument("--name", required=True)
    pn.add_argument("--claim-timeout", type=int, default=DEFAULT_CLAIM_TIMEOUT)
    pn.add_argument("--root", default=".")

    for op in ("done", "fail"):
        p = sub.add_parser(op)
        p.add_argument("--name", required=True)
        p.add_argument("--id", required=True)
        p.add_argument("--note", default="")
        if op == "fail":
            p.add_argument("--max-attempts", type=int, default=3)
        p.add_argument("--root", default=".")

    for op in ("status", "report"):
        p = sub.add_parser(op)
        p.add_argument("--name", required=True)
        p.add_argument("--root", default=".")

    args = ap.parse_args(argv)
    root = Path(args.root).resolve()

    if args.op == "init":
        return cmd_init(root, args.name, args.items_from, args.item, args.glob, args.force)
    if args.op == "next":
        return cmd_next(root, args.name, args.claim_timeout)
    if args.op == "done":
        return cmd_done(root, args.name, args.id, args.note)
    if args.op == "fail":
        return cmd_fail(root, args.name, args.id, args.note, args.max_attempts)
    if args.op == "status":
        return cmd_status(root, args.name)
    return cmd_report(root, args.name)


if __name__ == "__main__":
    raise SystemExit(main())
