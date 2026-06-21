"""Find email addresses for a lead's domain via Hunter.io (impl: P3).

CLI:
  python scripts/find_email.py ping
  python scripts/find_email.py run --domain acme.com   # P3
"""

from __future__ import annotations

import argparse

from _common import ConfigError, require_env, request

PROVIDER = "hunter"
BASE = "https://api.hunter.io"


def ping() -> dict:
    try:
        (key,) = require_env("HUNTER_API_KEY")
    except ConfigError as exc:
        return {"provider": PROVIDER, "ok": False, "detail": str(exc)}
    try:
        resp = request(PROVIDER, "GET", f"{BASE}/v2/account", params={"api_key": key})
        plan = resp.json().get("data", {}).get("plan_name", "unknown")
        return {"provider": PROVIDER, "ok": True, "detail": f"plan={plan}"}
    except Exception as exc:
        return {"provider": PROVIDER, "ok": False, "detail": str(exc)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ping", help="Check Hunter.io connectivity.")
    p_run = sub.add_parser("run", help="Find emails for a domain (P3).")
    p_run.add_argument("--domain")
    args = parser.parse_args()
    if args.cmd == "ping":
        r = ping()
        print(f"[{'OK' if r['ok'] else 'FAIL'}] {PROVIDER}: {r['detail']}")
        return 0 if r["ok"] else 1
    print("find_email: not yet implemented — scheduled for P3.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
