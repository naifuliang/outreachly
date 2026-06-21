"""LinkedIn discovery + DM via Unipile (impl: P5).

CLI:
  python scripts/linkedin.py ping
  python scripts/linkedin.py search --keywords "..."     # P5
  python scripts/linkedin.py dm --lead 1 --message "..."  # P5
"""

from __future__ import annotations

import argparse

from _common import ConfigError, require_env, request

PROVIDER = "unipile"


def ping() -> dict:
    try:
        dsn, key = require_env("UNIPILE_DSN", "UNIPILE_API_KEY")
    except ConfigError as exc:
        return {"provider": PROVIDER, "ok": False, "detail": str(exc)}
    try:
        resp = request(
            PROVIDER, "GET", f"{dsn.rstrip('/')}/api/v1/accounts",
            headers={"X-API-KEY": key, "accept": "application/json"},
        )
        data = resp.json()
        n = len(data.get("items", data if isinstance(data, list) else []))
        return {"provider": PROVIDER, "ok": True, "detail": f"{n} account(s)"}
    except Exception as exc:
        return {"provider": PROVIDER, "ok": False, "detail": str(exc)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ping", help="Check Unipile/LinkedIn connectivity.")
    p_s = sub.add_parser("search", help="Search LinkedIn leads (P5).")
    p_s.add_argument("--keywords")
    p_d = sub.add_parser("dm", help="Send a LinkedIn DM (P5).")
    p_d.add_argument("--lead")
    p_d.add_argument("--message")
    args = parser.parse_args()
    if args.cmd == "ping":
        r = ping()
        print(f"[{'OK' if r['ok'] else 'FAIL'}] {PROVIDER} (linkedin): {r['detail']}")
        return 0 if r["ok"] else 1
    print("linkedin: not yet implemented — scheduled for P5.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
