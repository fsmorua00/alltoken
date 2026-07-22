# Telemetry policy — none by default, opt-in aggregates only

alltoken's pitch includes "nothing leaves your machine", and that stays true.

## Default: zero network

Every bundled engine (audit, apply, usage, progress, compression) works
entirely on local files. No pings, no update checks, no analytics.

## The community benchmark (strictly opt-in)

Everyone in this niche *claims* savings. We measure them — on the user's own
data, shared only if the user chooses to. The flow:

1. `/alltoken` saves a local baseline of your usage metrics.
2. `/token-progress` shows your own before/after deltas, locally.
3. **If — and only if — you run `scripts/share_stats.py` and confirm with
   `--yes` after seeing the exact payload**, the aggregates go to the
   benchmark server, and the community medians become public at `/v1/stats`.

## What is sent (the whole schema)

```json
{
  "schema": 1,
  "anon_id": "<random UUID, generated locally>",
  "plugin_version": "0.6.0",
  "days_since_baseline": 14,
  "before": {"messages": 83, "total_tokens": 8800000, "tok_per_msg": 106000,
              "output_share_pct": 1.2, "cache_read_share_pct": 93.0,
              "frontier_share_pct": 98.0},
  "after":  {"...same five metrics..."}
}
```

## What is never sent (or even collected by the client)

Code. Prompts. File contents. File paths. Project names. Hostnames.
Usernames. Emails. IP-derived identity (the server keeps no IP↔report link;
rate limiting is in-memory only).

## Guarantees

- The server is open source in this repo (`server/`) and self-hostable —
  point `ALLTOKEN_ENDPOINT` anywhere, including your own box.
- The schema is enforced server-side: payloads with extra fields, oversized
  bodies, or non-numeric metrics are rejected.
- Public stats are labelled as self-reported medians, never as controlled-
  experiment results.
- Deleting `~/.claude/alltoken/anon_id` unlinks any future report from past ones.
