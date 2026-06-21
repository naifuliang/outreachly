"""Discover leads via the Google Places API and upsert them into the CRM (impl: P3).

CLI:
  python scripts/discover_maps.py ping
  python scripts/discover_maps.py run --query "dental clinics in Austin"   # P3
"""

from __future__ import annotations

import argparse

from _common import ConfigError, require_env, request

PROVIDER = "places"
BASE = "https://maps.googleapis.com"


def ping() -> dict:
    try:
        (key,) = require_env("GOOGLE_PLACES_API_KEY")
    except ConfigError as exc:
        return {"provider": PROVIDER, "ok": False, "detail": str(exc)}
    try:
        resp = request(
            PROVIDER, "GET", f"{BASE}/maps/api/place/findplacefromtext/json",
            params={"input": "coffee", "inputtype": "textquery", "key": key},
        )
        status = resp.json().get("status", "UNKNOWN")
        ok = status in {"OK", "ZERO_RESULTS"}
        return {"provider": PROVIDER, "ok": ok, "detail": f"status={status}"}
    except Exception as exc:
        return {"provider": PROVIDER, "ok": False, "detail": str(exc)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ping", help="Check Google Places connectivity.")
    p_run = sub.add_parser("run", help="Discover leads (P3).")
    p_run.add_argument("--query")
    args = parser.parse_args()
    if args.cmd == "ping":
        r = ping()
        print(f"[{'OK' if r['ok'] else 'FAIL'}] {PROVIDER}: {r['detail']}")
        return 0 if r["ok"] else 1
    print("discover_maps: not yet implemented — scheduled for P3.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
