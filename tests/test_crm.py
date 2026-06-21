"""P0: CRM init creates the four tables; upsert dedups."""

import crm


def test_init_creates_four_tables(tmp_path):
    db = str(tmp_path / "t.sqlite")
    tables = crm.init_db(db)
    assert crm.EXPECTED_TABLES <= tables


def test_init_is_idempotent(tmp_path):
    db = str(tmp_path / "t.sqlite")
    assert crm.init_db(db) == crm.init_db(db)


def test_upsert_dedups_by_email(tmp_path):
    db = str(tmp_path / "t.sqlite")
    crm.init_db(db)
    id1, created1 = crm.upsert_lead({"source": "maps", "name": "Acme", "email": "a@acme.com"}, db)
    id2, created2 = crm.upsert_lead({"source": "maps", "name": "Acme Inc", "email": "a@acme.com"}, db)
    assert created1 is True and created2 is False
    assert id1 == id2
    assert len(crm.list_leads(path=db)) == 1


def test_upsert_derives_domain(tmp_path):
    db = str(tmp_path / "t.sqlite")
    crm.init_db(db)
    crm.upsert_lead({"source": "maps", "name": "Acme", "website": "https://www.acme.com/x"}, db)
    assert crm.list_leads(path=db)[0]["domain"] == "acme.com"
