"""CRM: local SQLite store for leads, campaigns, messages, events.

Owns the schema and the data primitives the other scripts use: init, dedup-aware upsert,
ICP-match scoring, the lead status state machine, and listing.

CLI:
  python scripts/crm.py init                       # create the schema (idempotent)
  python scripts/crm.py list [--status new]        # list leads
  python scripts/crm.py add --source maps --name "Acme" --email a@acme.com   # (test helper)
  python scripts/crm.py rescore                     # score all leads against the active ICP
  python scripts/crm.py status --lead 1 --to contacted   # transition a lead's status
"""

from __future__ import annotations

import argparse
import json
from urllib.parse import urlsplit

from _common import connect

EXPECTED_TABLES = {"leads", "campaigns", "messages", "events"}

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS campaigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    icp TEXT, channels TEXT,
    status TEXT NOT NULL DEFAULT 'draft',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL, external_id TEXT,
    name TEXT, company TEXT, website TEXT, domain TEXT,
    email TEXT, email_status TEXT, phone TEXT, location TEXT, title TEXT,
    profile TEXT, score INTEGER DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'new',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_leads_source_external
    ON leads (source, external_id) WHERE external_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_leads_email ON leads (email) WHERE email IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_leads_domain ON leads (domain);
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads (status);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER REFERENCES leads(id) ON DELETE CASCADE,
    campaign_id INTEGER REFERENCES campaigns(id) ON DELETE SET NULL,
    channel TEXT NOT NULL, direction TEXT NOT NULL,
    sequence_step INTEGER DEFAULT 0,
    subject TEXT, body TEXT, status TEXT, intent TEXT,
    sent_at TEXT, created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_messages_lead ON messages (lead_id);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER REFERENCES leads(id) ON DELETE CASCADE,
    campaign_id INTEGER REFERENCES campaigns(id) ON DELETE SET NULL,
    type TEXT NOT NULL, payload TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_events_type ON events (type);
"""


def init_db(path: str | None = None) -> set[str]:
    conn = connect(path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        return {r["name"] for r in rows}
    finally:
        conn.close()


# Domains that do NOT identify a unique entity — URL shorteners and public platforms. A lead's
# website on these (e.g. a t.co link in an X bio) must never be used as a dedup key, or distinct
# people sharing such a domain would be wrongly merged into one lead.
NON_IDENTIFYING_DOMAINS = {
    "t.co", "bit.ly", "lnkd.in", "goo.gl", "ow.ly", "buff.ly", "linktr.ee", "beacons.ai",
    "instagram.com", "twitter.com", "x.com", "facebook.com", "fb.com", "youtube.com",
    "tiktok.com", "threads.net", "linkedin.com", "medium.com", "substack.com", "github.com",
}


def _domain(website: str | None) -> str | None:
    """Normalized website host usable as an identity key, or None for shorteners/platforms."""
    if not website:
        return None
    host = urlsplit(website if "//" in website else f"//{website}").hostname or ""
    host = host.lower().removeprefix("www.")
    if not host or host in NON_IDENTIFYING_DOMAINS:
        return None
    return host


def upsert_lead(lead: dict, path: str | None = None) -> tuple[int, bool]:
    """Insert or update a lead with dedup. Returns (lead_id, created).

    Dedup order: (source, external_id) → email → domain. Existing rows are updated in place.
    Domain is only used as a dedup key for leads that have neither an external_id nor an email
    (e.g. a website-only Maps lead). A lead with an external_id is uniquely identified by
    (source, external_id), so it must not be merged onto a different lead via a shared domain.
    """
    conn = connect(path)
    try:
        lead = {**lead}
        lead.setdefault("domain", _domain(lead.get("website")))
        if isinstance(lead.get("profile"), (dict, list)):
            lead["profile"] = json.dumps(lead["profile"], ensure_ascii=False)

        existing = None
        if lead.get("external_id"):
            existing = conn.execute(
                "SELECT id FROM leads WHERE source=? AND external_id=?",
                (lead.get("source"), lead["external_id"]),
            ).fetchone()
        if not existing and lead.get("email"):
            existing = conn.execute("SELECT id FROM leads WHERE email=?", (lead["email"],)).fetchone()
        # Domain dedup only for leads lacking a strong identity (no external_id, no email).
        if not existing and lead.get("domain") and not lead.get("external_id") and not lead.get("email"):
            existing = conn.execute(
                "SELECT id FROM leads WHERE domain=?", (lead["domain"],)
            ).fetchone()

        cols = [
            "source", "external_id", "name", "company", "website", "domain",
            "email", "email_status", "phone", "location", "title", "profile", "score", "status",
        ]
        if existing:
            sets = [f"{c}=COALESCE(?, {c})" for c in cols]
            conn.execute(
                f"UPDATE leads SET {', '.join(sets)}, updated_at=datetime('now') WHERE id=?",
                [lead.get(c) for c in cols] + [existing["id"]],
            )
            conn.commit()
            return existing["id"], False
        ins_cols = [c for c in cols if lead.get(c) is not None]  # let DEFAULTs apply otherwise
        placeholders = ", ".join("?" for _ in ins_cols)
        cur = conn.execute(
            f"INSERT INTO leads ({', '.join(ins_cols)}) VALUES ({placeholders})",
            [lead.get(c) for c in ins_cols],
        )
        conn.commit()
        return int(cur.lastrowid), True
    finally:
        conn.close()


def list_leads(status: str | None = None, path: str | None = None) -> list[dict]:
    conn = connect(path)
    try:
        if status:
            rows = conn.execute(
                "SELECT * FROM leads WHERE status=? ORDER BY score DESC, id DESC", (status,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM leads ORDER BY score DESC, id DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# --- ICP-match scoring (0-100) ---------------------------------------------------------------

def score_lead(lead: dict, icp: dict) -> int:
    """Score how well a lead matches an ICP, 0-100. Transparent weighted overlap:
    keywords 40, industries 25, titles 20, geographies 15 (full 15 if the ICP names no geos).
    """
    hay = " ".join(
        str(lead.get(k) or "")
        for k in ("name", "company", "website", "domain", "title", "location", "profile")
    ).lower()

    def frac_hit(terms: list[str]) -> float:
        terms = [t for t in terms if t]
        if not terms:
            return 0.0
        return sum(1 for t in terms if t.lower() in hay) / len(terms)

    def any_hit(terms: list[str]) -> bool:
        return any(t and t.lower() in hay for t in terms)

    score = 40 * frac_hit(icp.get("keywords", []))
    score += 25 if any_hit(icp.get("industries", [])) else 0
    score += 20 if any_hit(icp.get("titles", [])) else 0
    geos = [g for g in icp.get("geographies", []) if g]
    score += 15 if (not geos or any_hit(geos)) else 0
    return round(min(100.0, score))


def rescore_all(icp: dict, path: str | None = None) -> int:
    """Recompute every lead's score against `icp`. Returns the number of leads scored."""
    conn = connect(path)
    try:
        rows = conn.execute("SELECT * FROM leads").fetchall()
        for r in rows:
            conn.execute(
                "UPDATE leads SET score=?, updated_at=datetime('now') WHERE id=?",
                (score_lead(dict(r), icp), r["id"]),
            )
        conn.commit()
        return len(rows)
    finally:
        conn.close()


# --- Lead status state machine ---------------------------------------------------------------

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "new": {"contacted", "rejected"},
    "contacted": {"replied", "rejected"},
    "replied": {"converted", "rejected"},
    "converted": set(),
    "rejected": set(),
}


class IllegalTransition(ValueError):
    """Raised when a lead status change is not permitted by the state machine."""


def get_lead(lead_id: int, path: str | None = None) -> dict | None:
    conn = connect(path)
    try:
        row = conn.execute("SELECT * FROM leads WHERE id=?", (lead_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def set_status(lead_id: int, new_status: str, path: str | None = None) -> str:
    """Transition a lead's status, enforcing ALLOWED_TRANSITIONS. Returns the new status."""
    conn = connect(path)
    try:
        row = conn.execute("SELECT status FROM leads WHERE id=?", (lead_id,)).fetchone()
        if row is None:
            raise IllegalTransition(f"lead #{lead_id} not found")
        current = row["status"]
        if new_status not in ALLOWED_TRANSITIONS.get(current, set()):
            allowed = sorted(ALLOWED_TRANSITIONS.get(current, set())) or ["(terminal)"]
            raise IllegalTransition(
                f"illegal transition {current} → {new_status}; allowed from {current}: {allowed}"
            )
        conn.execute(
            "UPDATE leads SET status=?, updated_at=datetime('now') WHERE id=?",
            (new_status, lead_id),
        )
        conn.commit()
        return new_status
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Outreachly CRM (SQLite).")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init", help="Create the schema (idempotent).")
    p_list = sub.add_parser("list", help="List leads.")
    p_list.add_argument("--status")
    p_add = sub.add_parser("add", help="Add a test lead.")
    for f in ("source", "external-id", "name", "company", "website", "email"):
        p_add.add_argument(f"--{f}")
    sub.add_parser("rescore", help="Score all leads against the active ICP.")
    p_st = sub.add_parser("status", help="Transition a lead's status.")
    p_st.add_argument("--lead", type=int, required=True)
    p_st.add_argument("--to", required=True, dest="to")
    args = parser.parse_args()

    if args.cmd == "init":
        tables = init_db()
        missing = EXPECTED_TABLES - tables
        print(f"CRM initialized — {len(tables)} tables: {sorted(tables)}")
        return 1 if missing else 0
    if args.cmd == "list":
        for r in list_leads(args.status):
            print(f"#{r['id']:<4} [{r['status']:<9}] {r['name'] or '?'} <{r['email'] or '-'}>")
        return 0
    if args.cmd == "add":
        lid, created = upsert_lead(
            {
                "source": args.source or "manual",
                "external_id": args.external_id,
                "name": args.name,
                "company": args.company,
                "website": args.website,
                "email": args.email,
            }
        )
        print(f"{'created' if created else 'updated (dedup)'} lead #{lid}")
        return 0
    if args.cmd == "rescore":
        from icp import load_icp

        icp = load_icp()
        if icp is None:
            print("No active ICP — generate/save one first (scripts/icp.py).")
            return 1
        n = rescore_all(icp)
        print(f"Scored {n} lead(s) against the active ICP.")
        return 0
    if args.cmd == "status":
        try:
            new = set_status(args.lead, args.to)
        except IllegalTransition as exc:
            print(f"REJECTED: {exc}")
            return 1
        print(f"lead #{args.lead} → {new}")
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
