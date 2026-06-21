"""Pull replies from the channels, log them, and stop the sequence for repliers.

Division of labor: this script FETCHES inbound messages (Unipile unified inbox for LinkedIn +
email; X DM) and matches them to leads; CLAUDE classifies intent (interested / not_interested /
later) and calls `set_intent`. A matched reply advances the lead contacted → replied, which the
send scripts treat as "sequence stopped".

CLI:
  python scripts/reply_handler.py sync                         # pull replies, log inbound, mark replied
  python scripts/reply_handler.py set-intent --lead 3 --intent interested
"""

from __future__ import annotations

import argparse
import os

from _common import require_env, request

VALID_INTENTS = {"interested", "not_interested", "later"}


def record_reply(lead_id: int, channel: str, body: str, *, intent: str | None = None,
                 external_message_id: str | None = None, path: str | None = None) -> int:
    """Log an inbound message, advance contacted→replied, and event it. Returns message id."""
    import crm

    mid = crm.log_message(lead_id, channel, "inbound", body, intent=intent, path=path)
    crm.mark_replied(lead_id, path)
    crm.log_event("reply", lead_id=lead_id,
                  payload={"channel": channel, "external_message_id": external_message_id}, path=path)
    return mid


def set_intent(lead_id: int, intent: str, path: str | None = None) -> dict:
    """Persist Claude's intent classification onto the lead's latest inbound message."""
    import crm

    if intent not in VALID_INTENTS:
        return {"ok": False, "detail": f"intent must be one of {sorted(VALID_INTENTS)}"}
    msg = crm.latest_inbound(lead_id, path)
    if not msg:
        return {"ok": False, "detail": "no inbound message for this lead"}
    crm.set_message_intent(msg["id"], intent, path)
    return {"ok": True, "message_id": msg["id"], "intent": intent}


def _seen_reply_ids(path: str | None) -> set[str]:
    import json
    import crm

    conn = crm.connect(path)
    try:
        rows = conn.execute("SELECT payload FROM events WHERE type='reply'").fetchall()
    finally:
        conn.close()
    seen = set()
    for r in rows:
        try:
            ext = (json.loads(r["payload"]) or {}).get("external_message_id")
        except (TypeError, ValueError):
            ext = None
        if ext:
            seen.add(ext)
    return seen


def _fetch_unipile_inbound() -> list[dict]:
    """Inbound LinkedIn + email messages from Unipile. Defensive; [] if not configured."""
    dsn = os.environ.get("UNIPILE_DSN")
    key = os.environ.get("UNIPILE_API_KEY")
    if not (dsn and key):
        return []
    headers = {"X-API-KEY": key, "accept": "application/json"}
    out: list[dict] = []
    resp = request("unipile", "GET", f"{dsn.rstrip('/')}/api/v1/messages",
                   headers=headers, params={"limit": 50}, use_proxy=False)
    for m in resp.json().get("items", []):
        if str(m.get("direction") or m.get("is_sender") or "").lower() in ("out", "outbound", "true", "1"):
            continue
        out.append({
            "external_message_id": m.get("id"),
            "sender_id": m.get("sender_id") or m.get("attendee_provider_id"),
            "sender_email": m.get("from") or m.get("from_email"),
            "channel": (m.get("provider") or "linkedin").lower(),
            "body": m.get("text") or m.get("body") or "",
        })
    return out


# Unipile account types that are email mailboxes (Gmail=GOOGLE_OAUTH, Outlook=MICROSOFT/OUTLOOK).
_EMAIL_KINDS = ("GOOGLE", "GMAIL", "MICROSOFT", "OUTLOOK", "MAIL", "IMAP", "EMAIL")
# Email folders/roles that are NOT received replies.
_NON_INBOUND_ROLES = ("sent", "drafts", "draft", "trash", "spam", "junk")


def _fetch_unipile_emails() -> list[dict]:
    """Received emails (replies) from connected mailboxes via Unipile. Defensive; [] if unconfigured.

    Email shape differs from messaging: sender is `from_attendee.identifier`, direction is the
    `role`/folder, body is `body_plain`. Only received mail (not sent/drafts) is returned.
    """
    dsn = os.environ.get("UNIPILE_DSN")
    key = os.environ.get("UNIPILE_API_KEY")
    if not (dsn and key):
        return []
    base = dsn.rstrip("/")
    headers = {"X-API-KEY": key, "accept": "application/json"}
    accounts = request("unipile", "GET", f"{base}/api/v1/accounts", headers=headers, use_proxy=False)
    accounts = accounts.json()
    accounts = accounts.get("items", accounts if isinstance(accounts, list) else [])
    out: list[dict] = []
    for acc in accounts:
        kind = str(acc.get("type") or acc.get("provider") or "").upper()
        if not any(k in kind for k in _EMAIL_KINDS):
            continue
        aid = acc.get("id") or acc.get("account_id")
        resp = request("unipile", "GET", f"{base}/api/v1/emails", headers=headers,
                       params={"account_id": aid, "limit": 50}, use_proxy=False)
        for e in resp.json().get("items", []):
            if str(e.get("role") or "").lower() in _NON_INBOUND_ROLES:
                continue  # only received mail counts as a reply
            frm = e.get("from_attendee") or {}
            sender = frm.get("identifier") if isinstance(frm, dict) else None
            out.append({
                "external_message_id": e.get("id"),
                "sender_id": None,
                "sender_email": sender,
                "channel": "email",
                "body": e.get("body_plain") or e.get("body") or "",
            })
    return out


def _fetch_x_inbound() -> list[dict]:
    """Inbound X DMs. Defensive; [] if not configured."""
    token = os.environ.get("X_BEARER_TOKEN")
    if not token:
        return []
    resp = request("x", "GET", "https://api.twitter.com/2/dm_events",
                   headers={"Authorization": f"Bearer {token}"},
                   params={"dm_event.fields": "sender_id,text", "max_results": 50})
    out = []
    for e in resp.json().get("data", []):
        if e.get("event_type") and e.get("event_type") != "MessageCreate":
            continue
        out.append({
            "external_message_id": e.get("id"),
            "sender_id": e.get("sender_id"),
            "sender_email": None,
            "channel": "twitter",
            "body": e.get("text") or "",
        })
    return out


def sync(path: str | None = None) -> dict:
    """Fetch inbound from all configured providers, match to leads, record new replies."""
    import crm

    crm.init_db(path)  # ensure schema exists
    seen = _seen_reply_ids(path)
    inbound: list[dict] = []
    errors: list[str] = []
    for fetch in (_fetch_unipile_inbound, _fetch_unipile_emails, _fetch_x_inbound):
        try:  # best-effort: one provider failing must not abort the sync
            inbound += fetch()
        except Exception as exc:
            errors.append(str(exc))
    recorded = 0
    for m in inbound:
        if m.get("external_message_id") in seen:
            continue
        source = "twitter" if m["channel"] == "twitter" else ("linkedin" if m["channel"] in ("linkedin",) else None)
        lead = crm.find_lead_by(source=source, external_id=m.get("sender_id"),
                                email=m.get("sender_email"), path=path)
        if not lead:
            continue
        record_reply(lead["id"], m["channel"], m["body"],
                     external_message_id=m.get("external_message_id"), path=path)
        recorded += 1
    return {"fetched": len(inbound), "recorded": recorded, "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("sync", help="Pull replies, log inbound, mark repliers.")
    p_i = sub.add_parser("set-intent", help="Persist a classified intent on a lead's latest reply.")
    p_i.add_argument("--lead", type=int, required=True)
    p_i.add_argument("--intent", required=True, choices=sorted(VALID_INTENTS))
    args = parser.parse_args()

    if args.cmd == "sync":
        res = sync()
        print(f"replies: fetched {res['fetched']}, recorded {res['recorded']} new")
        for e in res.get("errors", []):
            print(f"  (provider skipped: {e})")
        return 0
    res = set_intent(args.lead, args.intent)
    print(res if not res.get("ok") else f"lead #{args.lead} reply → intent={res['intent']}")
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
