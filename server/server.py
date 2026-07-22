#!/usr/bin/env python3
"""
alltoken community benchmark server — receives OPT-IN aggregate reports and
serves public statistics. Pure Python stdlib + SQLite: no dependencies, runs
on any $5 Linux VPS with `python3 server.py`.

What it accepts (POST /v1/report): small JSON payloads of AGGREGATE metrics
only — tokens/message, output share, cache share, frontier share, before and
after. It rejects anything oversized or off-schema. It never receives code,
prompts, file paths, or hostnames; the client (share_stats.py) doesn't collect
them in the first place, and users see the exact payload before sending.

Endpoints:
  POST /v1/report   store one report (JSON, ≤ 8 KB)
  GET  /v1/stats    public aggregates: count + median deltas
  GET  /healthz     liveness probe

Config (env): ALLTOKEN_DB (default ./alltoken.db), PORT (8080), BIND (0.0.0.0)

Run behind a TLS reverse proxy (Caddy/nginx) in production — see README.md.
"""

from __future__ import annotations

import json
import os
import sqlite3
import statistics
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DB_PATH = os.environ.get("ALLTOKEN_DB", "./alltoken.db")
PORT = int(os.environ.get("PORT", "8080"))
BIND = os.environ.get("BIND", "0.0.0.0")
MAX_BODY = 8 * 1024
RATE_WINDOW_S = 3600
RATE_MAX = 20  # reports per IP per hour

_db_lock = threading.Lock()
_rate: dict[str, list[float]] = {}

METRIC_KEYS = ("tok_per_msg", "output_share_pct", "cache_read_share_pct", "frontier_share_pct", "messages")


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            received_at INTEGER NOT NULL,
            anon_id TEXT NOT NULL,
            plugin_version TEXT,
            days_since_baseline INTEGER,
            before_json TEXT NOT NULL,
            after_json TEXT NOT NULL
        )"""
    )
    return conn


def validate_metrics(block) -> bool:
    if not isinstance(block, dict):
        return False
    for k in METRIC_KEYS:
        v = block.get(k)
        if not isinstance(v, (int, float)) or v < 0 or v > 10_000_000_000:
            return False
    return True


def rate_limited(ip: str) -> bool:
    now = time.time()
    hits = [t for t in _rate.get(ip, []) if now - t < RATE_WINDOW_S]
    if len(hits) >= RATE_MAX:
        _rate[ip] = hits
        return True
    hits.append(now)
    _rate[ip] = hits
    return False


def compute_stats() -> dict:
    with _db_lock:
        conn = db()
        rows = conn.execute(
            "SELECT before_json, after_json FROM reports ORDER BY id DESC LIMIT 10000"
        ).fetchall()
        conn.close()
    deltas: dict[str, list[float]] = {"tok_per_msg": [], "output_share_pct": [], "cache_read_share_pct": []}
    for bj, aj in rows:
        try:
            b, a = json.loads(bj), json.loads(aj)
        except json.JSONDecodeError:
            continue
        for k in deltas:
            if b.get(k):
                deltas[k].append(100.0 * (a.get(k, 0) - b[k]) / b[k])
    out = {"reports": len(rows)}
    for k, vals in deltas.items():
        out[f"median_{k}_change_pct"] = round(statistics.median(vals), 1) if vals else None
    out["note"] = (
        "Self-reported, opt-in aggregates from real users. Workload changes "
        "affect these numbers; medians shown, not marketing claims."
    )
    return out


class Handler(BaseHTTPRequestHandler):
    server_version = "alltoken-benchmark/1.0"

    def _send(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):  # keep logs terse, no IPs beyond default
        pass

    def do_GET(self):
        if self.path == "/healthz":
            self._send(200, {"ok": True})
        elif self.path == "/v1/stats":
            self._send(200, compute_stats())
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/v1/report":
            self._send(404, {"error": "not found"})
            return
        ip = self.client_address[0]
        if rate_limited(ip):
            self._send(429, {"error": "rate limited"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0 or length > MAX_BODY:
            self._send(413, {"error": "body size"})
            return
        try:
            payload = json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._send(400, {"error": "invalid json"})
            return

        if (
            not isinstance(payload, dict)
            or payload.get("schema") != 1
            or not isinstance(payload.get("anon_id"), str)
            or len(payload.get("anon_id", "")) > 64
            or not validate_metrics(payload.get("before"))
            or not validate_metrics(payload.get("after"))
        ):
            self._send(400, {"error": "off schema"})
            return

        with _db_lock:
            conn = db()
            conn.execute(
                "INSERT INTO reports (received_at, anon_id, plugin_version, days_since_baseline, before_json, after_json) VALUES (?,?,?,?,?,?)",
                (
                    int(time.time()),
                    payload["anon_id"][:64],
                    str(payload.get("plugin_version", ""))[:32],
                    int(payload.get("days_since_baseline", 0) or 0),
                    json.dumps({k: payload["before"][k] for k in METRIC_KEYS}),
                    json.dumps({k: payload["after"][k] for k in METRIC_KEYS}),
                ),
            )
            conn.commit()
            conn.close()
        self._send(200, {"ok": True, "thanks": "aggregate stored — see /v1/stats"})


def main() -> None:
    db().close()  # ensure schema
    srv = ThreadingHTTPServer((BIND, PORT), Handler)
    print(f"alltoken benchmark server on {BIND}:{PORT} (db: {DB_PATH})")
    srv.serve_forever()


if __name__ == "__main__":
    main()
