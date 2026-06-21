"""CRM: local SQLite store for leads, campaigns, messages, events.

Owns the schema and the data primitives the other scripts use: init, dedup-aware upsert,
status transitions, and listing. Scoring/state-machine rules are filled in at P2.

CLI:
  python scripts/crm.py init                 # create the schema (idempotent)
  python scripts/crm.py list [--status new]  # list leads
  python scripts/crm.py add --source maps --name "Acme" --email a@acme.com   # (test helper)
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


def _domain(website: str | None) -> str | None:
    if not website:
        return None
    host = urlsplit(website if "//" in website else f"//{website}").hostname or ""
    return host.lower().removeprefix("www.") or None


def upsert_lead(lead: dict, path: str | None = None) -> tuple[int, bool]:
    """Insert or update a lead with dedup. Returns (lead_id, created).

    Dedup order: (source, external_id) → email → domain. Existing rows are updated in place.
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
        if not existing and lead.get("domain"):
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Outreachly CRM (SQLite).")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init", help="Create the schema (idempotent).")
    p_list = sub.add_parser("list", help="List leads.")
    p_list.add_argument("--status")
    p_add = sub.add_parser("add", help="Add a test lead.")
    for f in ("source", "external-id", "name", "company", "website", "email"):
        p_add.add_argument(f"--{f}")
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
