"""Send cold emails via Unipile (Gmail/Outlook) and log them to the CRM.

Claude writes the subject/body (personalized per lead); this script delivers and records it.
Draft mode (default) records the message as a draft and does NOT send; --auto actually sends.
Leads with email_status == 'invalid' (or no email) are refused — the send-queue guard.

CLI:
  python scripts/send_email.py ping
  python scripts/send_email.py run --lead 3 --subject "..." --body "..."          # draft
  python scripts/send_email.py run --lead 3 --subject "..." --body "..." --auto   # send
"""

from __future__ import annotations

import argparse

from _common import ConfigError, require_env, request

PROVIDER = "unipile"
CHANNEL = "email"


def _base_headers() -> tuple[str, dict]:
    dsn, key = require_env("UNIPILE_DSN", "UNIPILE_API_KEY")
    return dsn.rstrip("/"), {"X-API-KEY": key, "accept": "application/json",
                             "content-type": "application/json"}


def ping() -> dict:
    try:
        base, headers = _base_headers()
    except ConfigError as exc:
        return {"provider": PROVIDER, "ok": False, "detail": str(exc)}
    try:
        resp = request(PROVIDER, "GET", f"{base}/api/v1/accounts", headers=headers, use_proxy=False)
        data = resp.json()
        n = len(data.get("items", data if isinstance(data, list) else []))
        return {"provider": PROVIDER, "ok": True, "detail": f"{n} account(s)"}
    except Exception as exc:
        return {"provider": PROVIDER, "ok": False, "detail": str(exc)}


def _email_account_id(base: str, headers: dict) -> str | None:
    import os
    if os.environ.get("UNIPILE_EMAIL_ACCOUNT_ID"):
        return os.environ["UNIPILE_EMAIL_ACCOUNT_ID"]
    resp = request(PROVIDER, "GET", f"{base}/api/v1/accounts", headers=headers, use_proxy=False)
    items = resp.json().get("items", [])
    for it in items:
        kind = str(it.get("type") or it.get("provider") or "").upper()
        if any(k in kind for k in ("MAIL", "GMAIL", "OUTLOOK", "IMAP", "EMAIL")):
            return it.get("id") or it.get("account_id")
    return items[0].get("id") if items else None


def send_email(lead_id: int, subject: str, body: str, *, auto: bool = False,
               campaign_id: int | None = None, path: str | None = None) -> dict:
    """Draft (default) or send (auto) an email to a lead. Returns a summary dict."""
    import crm

    lead = crm.get_lead(lead_id, path)
    if not lead:
        return {"ok": False, "detail": f"lead #{lead_id} not found"}
    if lead.get("status") in crm.STOPPED_STATUSES:
        return {"ok": False, "detail": f"sequence stopped (status={lead['status']})"}
    if not lead.get("email"):
        return {"ok": False, "detail": "lead has no email"}
    if str(lead.get("email_status") or "").strip().lower() == "invalid":
        return {"ok": False, "detail": "email_status is invalid — refusing to send"}

    if auto:
        base, headers = _base_headers()
        account_id = _email_account_id(base, headers)
        if not account_id:
            raise ConfigError("No connected email account in Unipile.")
        request(
            PROVIDER, "POST", f"{base}/api/v1/emails",
            headers=headers, use_proxy=False,
            json={"account_id": account_id, "to": [{"identifier": lead["email"]}],
                  "subject": subject, "body": body},
        )

    status = "sent" if auto else "draft"
    mid = crm.log_message(lead_id, CHANNEL, "outbound", body, subject=subject,
                          status=status, campaign_id=campaign_id, path=path)
    if auto:
        crm.mark_contacted(lead_id, path)
    return {"ok": True, "message_id": mid, "status": status, "to": lead["email"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ping", help="Check Unipile connectivity.")
    p_run = sub.add_parser("run", help="Draft or send an email to a lead.")
    p_run.add_argument("--lead", type=int, required=True)
    p_run.add_argument("--subject", required=True)
    p_run.add_argument("--body", required=True)
    p_run.add_argument("--auto", action="store_true", help="Actually send (default: draft only).")
    args = parser.parse_args()

    if args.cmd == "ping":
        r = ping()
        print(f"[{'OK' if r['ok'] else 'FAIL'}] {PROVIDER} (email): {r['detail']}")
        return 0 if r["ok"] else 1
    try:
        res = send_email(args.lead, args.subject, args.body, auto=args.auto)
    except ConfigError as exc:
        print(f"FAIL: {exc}")
        return 1
    if not res["ok"]:
        print(f"REFUSED: {res['detail']}")
        return 1
    print(f"email {res['status']} → {res['to']} (msg #{res['message_id']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
