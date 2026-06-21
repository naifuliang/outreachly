"""Initialize the SQLite CRM from schema.sql.

CLI:  python -m app.db.init_db [--db PATH]
Idempotent: uses CREATE TABLE IF NOT EXISTS.
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from app.core.config import settings
from app.i18n import t

SCHEMA_PATH = Path(__file__).with_name("schema.sql")
EXPECTED_TABLES = {"leads", "campaigns", "messages", "events"}


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    path = Path(db_path or settings.db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: str | None = None) -> set[str]:
    """Create the schema and return the set of table names present afterward."""
    conn = get_connection(db_path)
    try:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.commit()
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        return {r["name"] for r in rows}
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize the Outreachly SQLite CRM.")
    parser.add_argument("--db", default=None, help="Path to the SQLite file.")
    parser.add_argument("--locale", default=None, help="Output locale: en | zh.")
    args = parser.parse_args()

    tables = init_db(args.db)
    print(t("db.initialized", locale=args.locale, path=args.db or settings.db_path, tables=len(tables)))

    missing = EXPECTED_TABLES - tables
    if missing:
        print(f"WARNING: expected tables missing: {sorted(missing)}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
