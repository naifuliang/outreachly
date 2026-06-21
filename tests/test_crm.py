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


def test_shortener_domain_is_not_an_identity(tmp_path):
    db = str(tmp_path / "t.sqlite")
    crm.init_db(db)
    crm.upsert_lead({"source": "twitter", "external_id": "u1", "name": "A",
                     "website": "https://t.co/abc"}, db)
    assert crm.list_leads(path=db)[0]["domain"] is None  # t.co never stored as identity


def test_social_leads_sharing_a_domain_are_not_merged(tmp_path):
    db = str(tmp_path / "t.sqlite")
    crm.init_db(db)
    # Two DISTINCT X users whose bios both link to the same site must stay two leads.
    crm.upsert_lead({"source": "twitter", "external_id": "u1", "name": "Alice",
                     "website": "https://hub.example/alice"}, db)
    crm.upsert_lead({"source": "twitter", "external_id": "u2", "name": "Bob",
                     "website": "https://hub.example/bob"}, db)
    assert len(crm.list_leads(path=db)) == 2


def test_website_only_leads_dedup_by_domain(tmp_path):
    db = str(tmp_path / "t.sqlite")
    crm.init_db(db)
    # No external_id, no email → domain is the dedup key (e.g. Maps website-only leads).
    crm.upsert_lead({"source": "maps", "name": "Acme", "website": "https://acme.com"}, db)
    _, created = crm.upsert_lead({"source": "maps", "name": "Acme Inc", "website": "http://acme.com/about"}, db)
    assert created is False
    assert len(crm.list_leads(path=db)) == 1


def test_website_only_lead_does_not_merge_onto_social_lead(tmp_path):
    db = str(tmp_path / "t.sqlite")
    crm.init_db(db)
    # A social lead (has external_id) stored a real domain; a later website-only lead at the
    # same domain is a different entity and must NOT merge onto it.
    crm.upsert_lead({"source": "twitter", "external_id": "u1", "name": "CEO Person",
                     "website": "https://acme.com"}, db)
    _, created = crm.upsert_lead({"source": "maps", "name": "Acme Storefront",
                                  "website": "https://acme.com"}, db)
    assert created is True
    assert len(crm.list_leads(path=db)) == 2
