"""Twitter/X discovery + DM via the X API v2.

Discovery (this phase): recent-search for tweets matching ICP keywords, collect the unique
authors, and upsert them as leads. DM sending is wired at a later phase (needs user-context OAuth).

CLI:
  python scripts/twitter.py ping
  python scripts/twitter.py search --keywords "indie coffee shop" --max 20
  python scripts/twitter.py dm --lead 1 --message "..."   # later phase
"""

from __future__ import annotations

import argparse
import json

from _common import ConfigError, require_env, request

PROVIDER = "x"
BASE = "https://api.twitter.com"


def _auth_header() -> dict:
    (token,) = require_env("X_BEARER_TOKEN")
    return {"Authorization": f"Bearer {token}"}


def ping() -> dict:
    try:
        headers = _auth_header()
    except ConfigError as exc:
        return {"provider": PROVIDER, "ok": False, "detail": str(exc)}
    try:
        resp = request(PROVIDER, "GET", f"{BASE}/2/users/by/username/X", headers=headers)
        data = resp.json()
        ok = "data" in data
        detail = f"resolved @{data['data']['username']}" if ok else str(data)[:120]
        return {"provider": PROVIDER, "ok": ok, "detail": detail}
    except Exception as exc:
        return {"provider": PROVIDER, "ok": False, "detail": str(exc)}


def _users_from_search(payload: dict) -> list[dict]:
    """Extract the unique author user objects from a v2 recent-search response."""
    users = {u["id"]: u for u in payload.get("includes", {}).get("users", []) if u.get("id")}
    return list(users.values())


def search_twitter(keywords: str, max_results: int = 10, path: str | None = None) -> dict:
    """Search recent tweets by keywords; upsert each unique author as a lead.

    Returns {"found": n, "created": c, "updated": u}.
    """
    import crm

    query = f"{keywords} -is:retweet"
    resp = request(
        PROVIDER, "GET", f"{BASE}/2/tweets/search/recent",
        headers=_auth_header(),
        params={
            "query": query,
            "max_results": max(10, min(max_results, 100)),
            "expansions": "author_id",
            "user.fields": "name,username,description,location,url,public_metrics",
        },
    )
    users = _users_from_search(resp.json())
    created = updated = 0
    for u in users:
        lead = {
            "source": "twitter",
            "external_id": u.get("id"),
            "name": u.get("name"),
            "website": u.get("url"),
            "location": u.get("location"),
            "title": None,
            "company": None,
            "profile": {
                "username": u.get("username"),
                "description": u.get("description"),
                "metrics": u.get("public_metrics"),
            },
        }
        _, was_created = crm.upsert_lead(lead, path)
        created += int(was_created)
        updated += int(not was_created)
    return {"found": len(users), "created": created, "updated": updated}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ping", help="Check X API connectivity.")
    p_s = sub.add_parser("search", help="Search X for leads by keywords.")
    p_s.add_argument("--keywords", required=True)
    p_s.add_argument("--max", type=int, default=10)
    p_d = sub.add_parser("dm", help="Send an X DM (later phase).")
    p_d.add_argument("--lead")
    p_d.add_argument("--message")
    args = parser.parse_args()

    if args.cmd == "ping":
        r = ping()
        print(f"[{'OK' if r['ok'] else 'FAIL'}] {PROVIDER} (twitter): {r['detail']}")
        return 0 if r["ok"] else 1
    if args.cmd == "search":
        try:
            res = search_twitter(args.keywords, args.max)
        except ConfigError as exc:
            print(f"FAIL: {exc}")
            return 1
        print(f"twitter: found {res['found']} author(s) — {res['created']} new, {res['updated']} updated")
        return 0
    print("twitter dm: not yet implemented — scheduled for a later phase.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
