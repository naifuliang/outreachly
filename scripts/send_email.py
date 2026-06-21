"""Send cold emails via Unipile (Gmail/Outlook) and log them to the CRM (impl: P4).

CLI:
  python scripts/send_email.py ping
  python scripts/send_email.py run --lead 1 --subject ... --body ...   # P4
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
    sub.add_parser("ping", help="Check Unipile connectivity.")
    p_run = sub.add_parser("run", help="Send an email (P4).")
    p_run.add_argument("--lead")
    p_run.add_argument("--subject")
    p_run.add_argument("--body")
    args = parser.parse_args()
    if args.cmd == "ping":
        r = ping()
        print(f"[{'OK' if r['ok'] else 'FAIL'}] {PROVIDER} (email): {r['detail']}")
        return 0 if r["ok"] else 1
    print("send_email: not yet implemented — scheduled for P4.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
