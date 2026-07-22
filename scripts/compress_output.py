#!/usr/bin/env python3
"""
alltoken compress — deterministic noise reduction for verbose command output.

Pipe a noisy command through this before it lands in Claude's context. It uses
plain, deterministic rules (no model, no network, no hallucination) to strip the
parts that carry no signal:

  * collapses runs of identical / near-identical lines (progress spam)
  * drops known boilerplate (download bars, npm funding notices, ANSI codes)
  * middle-truncates very long output, keeping head + tail (where errors live)
  * always preserves lines that look like errors/warnings/failures

Honest expectations: savings depend entirely on how noisy the input is. A tidy
build saves ~nothing; a 5,000-line install log or test run can shrink 80–95%.
It is lossy by design — use it for logs you'd skim, not for output you must read
verbatim.

Usage:
    <noisy command> 2>&1 | python compress_output.py
    python compress_output.py --max-lines 200 < build.log
"""

from __future__ import annotations

import argparse
import re
import sys

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
# Carriage-return progress bars: keep only the final state of the line.
CR_RE = re.compile(r"^.*\r(?!\n)")

# Lines we never want to drop, even inside a collapsed block.
KEEP_RE = re.compile(
    r"\b(error|err!|fail|failed|failure|exception|traceback|"
    r"warning|warn|fatal|panic|denied|refused|timeout|cannot|unable)\b",
    re.IGNORECASE,
)

# Pure boilerplate safe to discard outright.
BOILERPLATE_RE = re.compile(
    r"^(?:"
    r"\s*(?:added|removed|changed|audited)\s+\d+\s+packages?"  # npm summaries
    r"|\s*\d+\s+packages?\s+are\s+looking\s+for\s+funding"
    r"|\s*run\s+`npm\s+fund`.*"
    r"|\s*npm\s+(?:notice|warn\s+deprecated|WARN\s+deprecated).*"
    r"|\s*(?:Downloading|Fetching|Resolving|Extracting|Unpacking)\b.*"
    r"|\s*\[[=>\- ]*\]\s*\d+%.*"  # ascii progress bars
    r"|\s*\.{3,}\s*$"
    r")",
    re.IGNORECASE,
)


def normalize(line: str) -> str:
    line = ANSI_RE.sub("", line)
    if "\r" in line:
        line = line.rsplit("\r", 1)[-1]
    return line.rstrip("\n")


def collapse(lines: list[str]) -> tuple[list[str], int]:
    """Collapse consecutive duplicate lines, keeping error-ish lines intact."""
    out: list[str] = []
    dropped = 0
    prev = None
    run = 0
    for ln in lines:
        stripped = ln.strip()
        if not stripped:
            # collapse blank runs to a single blank
            if out and out[-1] == "":
                dropped += 1
                continue
            out.append("")
            prev, run = None, 0
            continue
        if BOILERPLATE_RE.match(ln) and not KEEP_RE.search(ln):
            dropped += 1
            continue
        if ln == prev and not KEEP_RE.search(ln):
            run += 1
            dropped += 1
            continue
        if run > 0:
            out.append(f"    … ({run} identical line(s) collapsed)")
        out.append(ln)
        prev, run = ln, 0
    if run > 0:
        out.append(f"    … ({run} identical line(s) collapsed)")
    return out, dropped


def middle_truncate(lines: list[str], max_lines: int) -> tuple[list[str], int]:
    if max_lines <= 0 or len(lines) <= max_lines:
        return lines, 0
    # Always keep every error-ish line; fill the rest from head and tail.
    keep_idx = {i for i, ln in enumerate(lines) if KEEP_RE.search(ln)}
    budget = max_lines - len(keep_idx)
    if budget < 0:
        # More error lines than budget — keep the errors, drop the rest.
        result = [ln for i, ln in enumerate(lines) if i in keep_idx]
        return result, len(lines) - len(result)
    head = budget // 2
    tail = budget - head
    head_idx = set(range(head))
    tail_idx = set(range(len(lines) - tail, len(lines)))
    chosen = sorted(keep_idx | head_idx | tail_idx)
    result: list[str] = []
    prev_i = -1
    for i in chosen:
        if i != prev_i + 1 and result:
            result.append(f"    … ({i - prev_i - 1} line(s) trimmed) …")
        result.append(lines[i])
        prev_i = i
    dropped = len(lines) - len([i for i in chosen])
    return result, dropped


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="alltoken output compressor")
    ap.add_argument(
        "--max-lines",
        type=int,
        default=200,
        help="cap output at N lines via middle-truncation (0 = no cap)",
    )
    ap.add_argument(
        "--stats",
        action="store_true",
        help="print a one-line compression summary to stderr",
    )
    args = ap.parse_args(argv)

    raw = sys.stdin.read()
    original_lines = [normalize(l) for l in raw.splitlines()]
    n_in = len(original_lines)

    collapsed, dropped_c = collapse(original_lines)
    final, dropped_t = middle_truncate(collapsed, args.max_lines)

    sys.stdout.write("\n".join(final))
    if final:
        sys.stdout.write("\n")

    if args.stats:
        chars_in = len(raw)
        chars_out = sum(len(l) + 1 for l in final)
        pct = 0 if chars_in == 0 else round(100 * (1 - chars_out / chars_in))
        if pct >= 0:
            detail = f"~{pct}% fewer chars"
        else:
            # Tiny inputs can grow: collapse annotations outweigh the removed
            # lines. Say so honestly instead of printing a negative saving.
            detail = "no saving (input too small — pays off on big logs)"
        sys.stderr.write(
            f"[alltoken] {n_in} → {len(final)} lines, "
            f"{detail} ({dropped_c} collapsed, {dropped_t} trimmed)\n"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
