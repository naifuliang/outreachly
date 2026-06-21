"""Verify email validity via NeverBounce; label valid/risky/invalid.

`invalid` emails must never enter the send queue — `send_email.py` checks `email_status`.

CLI:
  python scripts/verify_email.py ping
  python scripts/verify_email.py run --email a@acme.com
  python scripts/verify_email.py run --lead 3          # verify the lead's email, store the label
"""

from __future__ import annotations

import argparse

from _common import ConfigError, require_env, request

PROVIDER = "neverbounce"
BASE = "https://api.neverbounce.com"

# NeverBounce result → our label.
_LABELS = {
    "valid": "valid",
    "catchall": "risky",
    "unknown": "risky",
    "disposable": "invalid",
    "invalid": "invalid",
}


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


def verify(email: str) -> str:
    """Return our label: valid | risky | invalid (defaults to risky on unknown result)."""
    (key,) = require_env("NEVERBOUNCE_API_KEY")
    resp = request(PROVIDER, "GET", f"{BASE}/v4/single/check",
                   params={"key": key, "email": email})
    result = resp.json().get("result", "unknown")
    return _LABELS.get(result, "risky")


def verify_lead(lead_id: int, path: str | None = None) -> dict:
    import crm

    lead = crm.get_lead(lead_id, path)
    if not lead:
        return {"ok": False, "detail": f"lead #{lead_id} not found"}
    if not lead.get("email"):
        return {"ok": False, "detail": "lead has no email to verify"}
    label = verify(lead["email"])
    crm.update_lead(lead_id, {"email_status": label}, path)
    crm.log_event("email_verified", lead_id=lead_id,
                  payload={"email": lead["email"], "status": label}, path=path)
    return {"ok": True, "email": lead["email"], "status": label}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ping", help="Check NeverBounce connectivity.")
    p_run = sub.add_parser("run", help="Verify an email or a lead's email.")
    p_run.add_argument("--email")
    p_run.add_argument("--lead", type=int)
    args = parser.parse_args()

    if args.cmd == "ping":
        r = ping()
        print(f"[{'OK' if r['ok'] else 'FAIL'}] {PROVIDER}: {r['detail']}")
        return 0 if r["ok"] else 1
    try:
        if args.lead is not None:
            res = verify_lead(args.lead)
            print(res if not res.get("ok") else f"lead #{args.lead}: {res['email']} → {res['status']}")
            return 0 if res.get("ok") else 1
        if args.email:
            print(f"{args.email} → {verify(args.email)}")
            return 0
    except ConfigError as exc:
        print(f"FAIL: {exc}")
        return 1
    print("verify_email: pass --email or --lead")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
