# alltoken community benchmark server

A tiny, dependency-free server (Python stdlib + SQLite) that receives **opt-in**
aggregate before/after reports from alltoken users and publishes community
medians. This is how "one command saves tokens" stops being a claim and becomes
a measured, public number.

## Privacy commitments (enforced by design)

- **Opt-in only.** The plugin never sends anything by default. Users run the
  share step explicitly and see the exact payload before it leaves the machine.
- **Aggregates only.** The schema accepts five numeric metrics per side
  (tokens/message, output share, cache-read share, frontier share, message
  count) and rejects everything else. No code, no prompts, no paths, no
  hostnames — the client doesn't even collect them.
- **Anonymous.** `anon_id` is a random UUID generated locally, unlinked to
  anything.
- **Public output.** `/v1/stats` shows count + median deltas, labelled as
  self-reported data, not marketing claims.

## Deploy (any Linux VPS, ~5 minutes)

```bash
# 1. copy the server folder
scp -r server/ you@your-vps:~/alltoken-server && ssh you@your-vps

# 2. run it (python3 is preinstalled on virtually every distro)
cd ~/alltoken-server
ALLTOKEN_DB=/var/lib/alltoken/alltoken.db PORT=8080 python3 server.py
```

### As a systemd service

```bash
sudo mkdir -p /var/lib/alltoken
sudo cp alltoken-server.service /etc/systemd/system/
# edit the paths/user inside if needed, then:
sudo systemctl daemon-reload
sudo systemctl enable --now alltoken-server
curl -s localhost:8080/healthz    # → {"ok": true}
```

### TLS (required for production)

Put Caddy in front — it handles certificates automatically:

```bash
sudo apt install caddy
# /etc/caddy/Caddyfile:
#   benchmark.yourdomain.com {
#       reverse_proxy localhost:8080
#   }
sudo systemctl reload caddy
```

Then point clients at it: `export ALLTOKEN_ENDPOINT=https://benchmark.yourdomain.com`

## API

| Endpoint | Method | Purpose |
|---|---|---|
| `/v1/report` | POST | Store one report (JSON ≤ 8 KB, schema-validated, 20/h/IP rate limit) |
| `/v1/stats` | GET | Public aggregates: report count + median deltas |
| `/healthz` | GET | Liveness |

Example stats response:

```json
{
  "reports": 128,
  "median_tok_per_msg_change_pct": -18.5,
  "median_output_share_pct_change_pct": -31.0,
  "median_cache_read_share_pct_change_pct": 12.4,
  "note": "Self-reported, opt-in aggregates from real users..."
}
```

## Client side

Users share with `scripts/share_stats.py` (in the plugin), which prints the
exact payload and requires explicit confirmation. See `docs/telemetry.md` in
the repo root for the full policy.
