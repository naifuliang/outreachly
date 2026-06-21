"""Twitter/X discovery + DM via the X API v2 (impl: P5).

CLI:
  python scripts/twitter.py ping
  python scripts/twitter.py search --keywords "..."     # P5
  python scripts/twitter.py dm --lead 1 --message "..."  # P5
"""

from __future__ import annotations

import argparse

from _common import ConfigError, require_env, request

PROVIDER = "x"
BASE = "https://api.twitter.com"


def ping() -> dict:
    try:
        (token,) = require_env("X_BEARER_TOKEN")
    except ConfigError as exc:
        return {"provider": PROVIDER, "ok": False, "detail": str(exc)}
    try:
        resp = request(
            PROVIDER, "GET", f"{BASE}/2/users/by/username/X",
            headers={"Authorization": f"Bearer {token}"},
        )
        data = resp.json()
        ok = "data" in data
        detail = f"resolved @{data['data']['username']}" if ok else str(data)[:120]
        return {"provider": PROVIDER, "ok": ok, "detail": detail}
    except Exception as exc:
        return {"provider": PROVIDER, "ok": False, "detail": str(exc)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ping", help="Check X API connectivity.")
    p_s = sub.add_parser("search", help="Search X leads (P5).")
    p_s.add_argument("--keywords")
    p_d = sub.add_parser("dm", help="Send an X DM (P5).")
    p_d.add_argument("--lead")
    p_d.add_argument("--message")
    args = parser.parse_args()
    if args.cmd == "ping":
        r = ping()
        print(f"[{'OK' if r['ok'] else 'FAIL'}] {PROVIDER} (twitter): {r['detail']}")
        return 0 if r["ok"] else 1
    print("twitter: not yet implemented — scheduled for P5.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
