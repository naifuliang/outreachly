"""Find email addresses for a lead's domain via Hunter.io.

Sources the domain from a discovered lead (e.g. a LinkedIn company site or an X bio link) and
attaches the best-confidence email back to that lead in the CRM.

CLI:
  python scripts/find_email.py ping
  python scripts/find_email.py run --domain acme.com
  python scripts/find_email.py run --lead 3            # use the lead's stored domain, save best email
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


def find_emails(domain: str) -> list[dict]:
    """Return candidate emails for a domain, highest confidence first.

    Each item: {email, confidence, first_name, last_name, position}.
    """
    (key,) = require_env("HUNTER_API_KEY")
    resp = request(PROVIDER, "GET", f"{BASE}/v2/domain-search",
                   params={"domain": domain, "api_key": key})
    emails = resp.json().get("data", {}).get("emails", [])
    out = [
        {
            "email": e.get("value"),
            "confidence": e.get("confidence") or 0,
            "first_name": e.get("first_name"),
            "last_name": e.get("last_name"),
            "position": e.get("position"),
        }
        for e in emails if e.get("value")
    ]
    out.sort(key=lambda x: x["confidence"], reverse=True)
    return out


def enrich_lead(lead_id: int, path: str | None = None) -> dict:
    """Find the best email for a lead's domain and store it. Returns a small summary."""
    import crm

    lead = crm.get_lead(lead_id, path)
    if not lead:
        return {"ok": False, "detail": f"lead #{lead_id} not found"}
    domain = lead.get("domain")
    if not domain:
        return {"ok": False, "detail": "lead has no domain to search"}
    candidates = find_emails(domain)
    if not candidates:
        crm.log_event("email_search", lead_id=lead_id, payload={"domain": domain, "found": 0}, path=path)
        return {"ok": True, "found": 0, "email": None}
    best = candidates[0]
    crm.update_lead(lead_id, {"email": best["email"], "email_status": "unknown"}, path)
    crm.log_event("email_found", lead_id=lead_id,
                  payload={"domain": domain, "email": best["email"], "confidence": best["confidence"]},
                  path=path)
    return {"ok": True, "found": len(candidates), "email": best["email"], "confidence": best["confidence"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ping", help="Check Hunter.io connectivity.")
    p_run = sub.add_parser("run", help="Find emails for a domain or a lead.")
    p_run.add_argument("--domain")
    p_run.add_argument("--lead", type=int)
    args = parser.parse_args()

    if args.cmd == "ping":
        r = ping()
        print(f"[{'OK' if r['ok'] else 'FAIL'}] {PROVIDER}: {r['detail']}")
        return 0 if r["ok"] else 1
    try:
        if args.lead is not None:
            res = enrich_lead(args.lead)
            print(res if not res.get("ok") else
                  f"lead #{args.lead}: {res['found']} candidate(s), best={res.get('email')}")
            return 0 if res.get("ok") else 1
        if args.domain:
            for e in find_emails(args.domain):
                print(f"  {e['confidence']:>3}  {e['email']}  ({e.get('position') or '-'})")
            return 0
    except ConfigError as exc:
        print(f"FAIL: {exc}")
        return 1
    print("find_email: pass --domain or --lead")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
