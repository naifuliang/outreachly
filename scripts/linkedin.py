"""LinkedIn discovery + DM via Unipile.

Discovery (this phase): search LinkedIn for people matching ICP keywords (via a connected
Unipile LinkedIn account) and upsert them as leads. DM is wired at a later phase.

Field mapping is defensive: Unipile's people-search item shapes vary, so we read several
possible keys. Confirm the mapping against live data once a Unipile account is connected.

CLI:
  python scripts/linkedin.py ping
  python scripts/linkedin.py search --keywords "head of marketing fintech" --max 20
  python scripts/linkedin.py dm --lead 1 --message "..."   # later phase
"""

from __future__ import annotations

import argparse
import os

from _common import ConfigError, require_env, request

PROVIDER = "unipile"


def _base_and_headers() -> tuple[str, dict]:
    dsn, key = require_env("UNIPILE_DSN", "UNIPILE_API_KEY")
    return dsn.rstrip("/"), {"X-API-KEY": key, "accept": "application/json",
                             "content-type": "application/json"}


def ping() -> dict:
    try:
        base, headers = _base_and_headers()
    except ConfigError as exc:
        return {"provider": PROVIDER, "ok": False, "detail": str(exc)}
    try:
        resp = request(PROVIDER, "GET", f"{base}/api/v1/accounts", headers=headers, use_proxy=False)
        data = resp.json()
        items = data.get("items", data if isinstance(data, list) else [])
        return {"provider": PROVIDER, "ok": True, "detail": f"{len(items)} account(s)"}
    except Exception as exc:
        return {"provider": PROVIDER, "ok": False, "detail": str(exc)}


def linkedin_account_id(base: str, headers: dict) -> str | None:
    """Find a connected LinkedIn account id (or use UNIPILE_ACCOUNT_ID override)."""
    override = os.environ.get("UNIPILE_ACCOUNT_ID")
    if override:
        return override
    resp = request(PROVIDER, "GET", f"{base}/api/v1/accounts", headers=headers, use_proxy=False)
    data = resp.json()
    items = data.get("items", data if isinstance(data, list) else [])
    for it in items:
        kind = str(it.get("type") or it.get("provider") or "").upper()
        if "LINKEDIN" in kind:
            return it.get("id") or it.get("account_id")
    return items[0].get("id") if items else None


def _parse_item(it: dict) -> dict:
    name = it.get("name") or " ".join(
        x for x in (it.get("first_name"), it.get("last_name")) if x
    ) or None
    return {
        "source": "linkedin",
        "external_id": (it.get("id") or it.get("member_id")
                        or it.get("public_identifier") or it.get("entity_urn")),
        "name": name,
        "title": it.get("headline") or it.get("title") or it.get("occupation"),
        "company": it.get("company") or it.get("current_company"),
        "location": it.get("location"),
        "profile": it,
    }


def search_linkedin(keywords: str, max_results: int = 10, path: str | None = None) -> dict:
    """Search LinkedIn people by keywords; upsert each as a lead.

    Returns {"found": n, "created": c, "updated": u}.
    """
    import crm

    base, headers = _base_and_headers()
    account_id = linkedin_account_id(base, headers)
    if not account_id:
        raise ConfigError("No connected LinkedIn account in Unipile (connect one in the dashboard).")

    resp = request(
        PROVIDER, "POST", f"{base}/api/v1/linkedin/search",
        headers=headers,
        params={"account_id": account_id, "limit": max(1, min(max_results, 50))},
        json={"api": "classic", "category": "people", "keywords": keywords},
        use_proxy=False,
    )
    data = resp.json()
    items = data.get("items", data if isinstance(data, list) else [])
    created = updated = 0
    for it in items:
        lead = _parse_item(it)
        if not (lead["external_id"] or lead["name"]):
            continue
        _, was_created = crm.upsert_lead(lead, path)
        created += int(was_created)
        updated += int(not was_created)
    return {"found": len(items), "created": created, "updated": updated}


def dm(lead_id: int, message: str, *, auto: bool = False, step: int = 0, path: str | None = None) -> dict:
    """Draft (default) or send (auto) a LinkedIn DM to a lead. Returns a summary dict."""
    import crm

    lead = crm.get_lead(lead_id, path)
    if not lead:
        return {"ok": False, "detail": f"lead #{lead_id} not found"}
    if lead.get("status") in crm.STOPPED_STATUSES:
        return {"ok": False, "detail": f"sequence stopped (status={lead['status']})"}
    if lead.get("source") != "linkedin" or not lead.get("external_id"):
        return {"ok": False, "detail": "lead is not a LinkedIn profile with an id"}

    if auto:
        base, headers = _base_and_headers()
        account_id = linkedin_account_id(base, headers)
        if not account_id:
            raise ConfigError("No connected LinkedIn account in Unipile.")
        request(
            PROVIDER, "POST", f"{base}/api/v1/chats",
            headers=headers, use_proxy=False,
            json={"account_id": account_id, "attendees_ids": [lead["external_id"]], "text": message},
        )

    status = "sent" if auto else "draft"
    mid = crm.log_message(lead_id, "linkedin", "outbound", message, status=status, sequence_step=step, path=path)
    if auto:
        crm.mark_contacted(lead_id, path)
    return {"ok": True, "message_id": mid, "status": status}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ping", help="Check Unipile/LinkedIn connectivity.")
    p_s = sub.add_parser("search", help="Search LinkedIn for leads by keywords.")
    p_s.add_argument("--keywords", required=True)
    p_s.add_argument("--max", type=int, default=10)
    p_d = sub.add_parser("dm", help="Draft or send a LinkedIn DM to a lead.")
    p_d.add_argument("--lead", type=int, required=True)
    p_d.add_argument("--message", required=True)
    p_d.add_argument("--auto", action="store_true", help="Actually send (default: draft only).")
    p_d.add_argument("--step", type=int, default=0, help="Sequence step (0=first touch).")
    args = parser.parse_args()

    if args.cmd == "ping":
        r = ping()
        print(f"[{'OK' if r['ok'] else 'FAIL'}] {PROVIDER} (linkedin): {r['detail']}")
        return 0 if r["ok"] else 1
    if args.cmd == "search":
        try:
            res = search_linkedin(args.keywords, args.max)
        except ConfigError as exc:
            print(f"FAIL: {exc}")
            return 1
        print(f"linkedin: found {res['found']} — {res['created']} new, {res['updated']} updated")
        return 0
    try:
        res = dm(args.lead, args.message, auto=args.auto, step=args.step)
    except ConfigError as exc:
        print(f"FAIL: {exc}")
        return 1
    if not res["ok"]:
        print(f"REFUSED: {res['detail']}")
        return 1
    print(f"linkedin DM {res['status']} → lead #{args.lead} (msg #{res['message_id']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
