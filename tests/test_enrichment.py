"""Email enrichment (Hunter/NeverBounce mocked) + CRM message/event/update helpers."""

import crm
import find_email
import verify_email


class FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


# --- CRM data layer ---

def test_update_lead_whitelists_columns(tmp_path):
    db = str(tmp_path / "t.sqlite")
    crm.init_db(db)
    lid, _ = crm.upsert_lead({"source": "linkedin", "external_id": "u1", "name": "A"}, db)
    crm.update_lead(lid, {"email": "a@acme.com", "status": "converted"}, db)  # status ignored here
    lead = crm.get_lead(lid, db)
    assert lead["email"] == "a@acme.com"
    assert lead["status"] == "new"  # update_lead must not change status


def test_log_and_list_messages(tmp_path):
    db = str(tmp_path / "t.sqlite")
    crm.init_db(db)
    lid, _ = crm.upsert_lead({"source": "linkedin", "external_id": "u1", "name": "A"}, db)
    mid = crm.log_message(lid, "email", "outbound", "hello", subject="hi", status="sent", path=db)
    assert mid > 0
    msgs = crm.list_messages(lid, db)
    assert len(msgs) == 1 and msgs[0]["direction"] == "outbound" and msgs[0]["sent_at"]


def test_log_event(tmp_path):
    db = str(tmp_path / "t.sqlite")
    crm.init_db(db)
    eid = crm.log_event("discovered", lead_id=None, payload={"k": "v"}, path=db)
    assert eid > 0


# --- find_email (Hunter mocked) ---

HUNTER = {"data": {"emails": [
    {"value": "low@acme.com", "confidence": 50, "position": "Intern"},
    {"value": "ceo@acme.com", "confidence": 95, "first_name": "Jane", "position": "CEO"},
]}}


def test_find_emails_sorted_by_confidence(monkeypatch):
    monkeypatch.setattr(find_email, "require_env", lambda *a: ("k",))
    monkeypatch.setattr(find_email, "request", lambda *a, **k: FakeResp(HUNTER))
    out = find_email.find_emails("acme.com")
    assert [e["email"] for e in out] == ["ceo@acme.com", "low@acme.com"]


def test_enrich_lead_saves_best_email(tmp_path, monkeypatch):
    db = str(tmp_path / "t.sqlite")
    crm.init_db(db)
    lid, _ = crm.upsert_lead({"source": "linkedin", "external_id": "u1", "name": "A",
                              "website": "https://acme.com"}, db)
    monkeypatch.setattr(find_email, "require_env", lambda *a: ("k",))
    monkeypatch.setattr(find_email, "request", lambda *a, **k: FakeResp(HUNTER))
    res = find_email.enrich_lead(lid, db)
    assert res["ok"] and res["email"] == "ceo@acme.com"
    assert crm.get_lead(lid, db)["email"] == "ceo@acme.com"


def test_enrich_lead_without_domain(tmp_path, monkeypatch):
    db = str(tmp_path / "t.sqlite")
    crm.init_db(db)
    lid, _ = crm.upsert_lead({"source": "twitter", "external_id": "u9", "name": "NoSite"}, db)
    res = find_email.enrich_lead(lid, db)
    assert res["ok"] is False and "domain" in res["detail"]


# --- verify_email (NeverBounce mocked) ---

def test_verify_label_mapping(monkeypatch):
    for result, expected in [("valid", "valid"), ("disposable", "invalid"),
                             ("invalid", "invalid"), ("catchall", "risky"), ("unknown", "risky")]:
        monkeypatch.setattr(verify_email, "require_env", lambda *a: ("k",))
        monkeypatch.setattr(verify_email, "request", lambda *a, r=result, **k: FakeResp({"result": r}))
        assert verify_email.verify("x@acme.com") == expected


def test_verify_lead_sets_status(tmp_path, monkeypatch):
    db = str(tmp_path / "t.sqlite")
    crm.init_db(db)
    lid, _ = crm.upsert_lead({"source": "linkedin", "external_id": "u1", "name": "A",
                              "email": "a@acme.com"}, db)
    monkeypatch.setattr(verify_email, "require_env", lambda *a: ("k",))
    monkeypatch.setattr(verify_email, "request", lambda *a, **k: FakeResp({"result": "invalid"}))
    res = verify_email.verify_lead(lid, db)
    assert res["status"] == "invalid"
    assert crm.get_lead(lid, db)["email_status"] == "invalid"
