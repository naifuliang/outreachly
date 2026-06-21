"""Outreach send: draft vs auto, message logging, status advance, and guards (HTTP mocked)."""

import crm
import linkedin
import send_email
import twitter


class FakeResp:
    def json(self):
        return {}


def _lead(db, **over):
    base = {"source": "linkedin", "external_id": "u1", "name": "A"}
    base.update(over)
    lid, _ = crm.upsert_lead(base, db)
    return lid


# --- send_email ---

def test_email_draft_logs_but_does_not_send_or_advance(tmp_path):
    db = str(tmp_path / "t.sqlite")
    crm.init_db(db)
    lid = _lead(db, email="a@acme.com", email_status="valid")
    res = send_email.send_email(lid, "Hi", "Body", auto=False, path=db)
    assert res["ok"] and res["status"] == "draft"
    assert crm.get_lead(lid, db)["status"] == "new"  # draft is not a real touch
    assert crm.list_messages(lid, db)[0]["status"] == "draft"


def test_email_auto_sends_and_advances(tmp_path, monkeypatch):
    db = str(tmp_path / "t.sqlite")
    crm.init_db(db)
    lid = _lead(db, email="a@acme.com", email_status="valid")
    monkeypatch.setattr(send_email, "_base_headers", lambda: ("https://api", {}))
    monkeypatch.setattr(send_email, "_email_account_id", lambda b, h: "acc")
    monkeypatch.setattr(send_email, "request", lambda *a, **k: FakeResp())
    res = send_email.send_email(lid, "Hi", "Body", auto=True, path=db)
    assert res["status"] == "sent"
    assert crm.get_lead(lid, db)["status"] == "contacted"


def test_email_refuses_invalid(tmp_path):
    db = str(tmp_path / "t.sqlite")
    crm.init_db(db)
    lid = _lead(db, email="a@acme.com", email_status="invalid")
    res = send_email.send_email(lid, "Hi", "Body", path=db)
    assert res["ok"] is False and "invalid" in res["detail"]


def test_email_refuses_no_email(tmp_path):
    db = str(tmp_path / "t.sqlite")
    crm.init_db(db)
    lid = _lead(db)
    res = send_email.send_email(lid, "Hi", "Body", path=db)
    assert res["ok"] is False


# --- linkedin dm ---

def test_linkedin_dm_draft(tmp_path):
    db = str(tmp_path / "t.sqlite")
    crm.init_db(db)
    lid = _lead(db)
    res = linkedin.dm(lid, "hey", auto=False, path=db)
    assert res["status"] == "draft"
    assert crm.get_lead(lid, db)["status"] == "new"


def test_linkedin_dm_auto_advances(tmp_path, monkeypatch):
    db = str(tmp_path / "t.sqlite")
    crm.init_db(db)
    lid = _lead(db)
    monkeypatch.setattr(linkedin, "_base_and_headers", lambda: ("https://api", {}))
    monkeypatch.setattr(linkedin, "linkedin_account_id", lambda b, h: "acc")
    monkeypatch.setattr(linkedin, "request", lambda *a, **k: FakeResp())
    res = linkedin.dm(lid, "hey", auto=True, path=db)
    assert res["status"] == "sent"
    assert crm.get_lead(lid, db)["status"] == "contacted"


def test_linkedin_dm_refuses_non_linkedin(tmp_path):
    db = str(tmp_path / "t.sqlite")
    crm.init_db(db)
    lid = _lead(db, source="twitter", external_id="x1")
    assert linkedin.dm(lid, "hey", path=db)["ok"] is False


# --- twitter dm ---

def test_twitter_dm_auto_advances(tmp_path, monkeypatch):
    db = str(tmp_path / "t.sqlite")
    crm.init_db(db)
    lid = _lead(db, source="twitter", external_id="x1")
    monkeypatch.setattr(twitter, "_dm_auth", lambda m, u: {"Authorization": "OAuth x"})
    monkeypatch.setattr(twitter, "request", lambda *a, **k: FakeResp())
    res = twitter.dm(lid, "hey", auto=True, path=db)
    assert res["status"] == "sent"
    assert crm.get_lead(lid, db)["status"] == "contacted"


def test_twitter_dm_refuses_non_twitter(tmp_path):
    db = str(tmp_path / "t.sqlite")
    crm.init_db(db)
    lid = _lead(db)  # source linkedin
    assert twitter.dm(lid, "hey", path=db)["ok"] is False
