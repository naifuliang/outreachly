"""P0: init_db creates the four core tables."""

from app.db.init_db import EXPECTED_TABLES, init_db


def test_init_db_creates_four_tables(tmp_path):
    db = tmp_path / "test.sqlite"
    tables = init_db(str(db))
    assert EXPECTED_TABLES <= tables
    assert db.exists()


def test_init_db_is_idempotent(tmp_path):
    db = tmp_path / "test.sqlite"
    first = init_db(str(db))
    second = init_db(str(db))
    assert first == second
