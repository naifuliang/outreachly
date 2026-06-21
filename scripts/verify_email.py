"""Verify email validity via NeverBounce; label valid/risky/invalid (impl: P3).

`invalid` emails must never enter the send queue.

CLI:
  python scripts/verify_email.py ping
  python scripts/verify_email.py run --email a@acme.com   # P3
"""

from __future__ import annotations

import argparse

from _common import ConfigError, require_env, request

PROVIDER = "neverbounce"
BASE = "https://api.neverbounce.com"


def ping() -> dict:
    try:
        (key,) = require_env("NEVERBOUNCE_API_KEY")
    except ConfigError as exc:
        return {"provider": PROVIDER, "ok": False, "detail": str(exc)}
    try:
        resp = request(PROVIDER, "GET", f"{BASE}/v4/account/info", params={"key": key})
        ok = resp.json().get("status") == "success"
        return {"provider": PROVIDER, "ok": ok, "detail": "account ok" if ok else "bad key"}
    except Exception as exc:
        return {"provider": PROVIDER, "ok": False, "detail": str(exc)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ping", help="Check NeverBounce connectivity.")
    p_run = sub.add_parser("run", help="Verify an email (P3).")
    p_run.add_argument("--email")
    args = parser.parse_args()
    if args.cmd == "ping":
        r = ping()
        print(f"[{'OK' if r['ok'] else 'FAIL'}] {PROVIDER}: {r['detail']}")
        return 0 if r["ok"] else 1
    print("verify_email: not yet implemented — scheduled for P3.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
