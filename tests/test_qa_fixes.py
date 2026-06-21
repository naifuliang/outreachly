"""Regression tests for the final-QA findings (draft sent_at, reply matching, dup email,
uninit-DB, new->replied, ICP path isolation)."""

from datetime import datetime, timedelta, timezone

import pytest

import crm
import find_email
import icp
import reply_handler
import sequence


def _now(days=0):
    return datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=days)


# --- #1 drafts must not be stamped sent_at and must not drive cadence ---

def test_draft_outbound_has_null_sent_at(tmp_path):
    db = str(tmp_path / "t.sqlite")
    crm.init_db(db)
    lid, _ = crm.upsert_lead({"source": "linkedin", "external_id": "u1", "name": "A"}, db)
    crm.log_message(lid, "linkedin", "outbound", "draft body", status="draft", path=db)
    assert crm.list_messages(lid, db)[0]["sent_at"] is None


def test_inbound_has_null_sent_at(tmp_path):
    db = str(tmp_path / "t.sqlite")
    crm.init_db(db)
    lid, _ = crm.upsert_lead({"source": "linkedin", "external_id": "u1", "name": "A"}, db)
    crm.log_message(lid, "linkedin", "inbound", "reply", path=db)
    assert crm.list_messages(lid, db)[0]["sent_at"] is None


def test_draft_does_not_drive_cadence(tmp_path):
    db = str(tmp_path / "t.sqlite")
    crm.init_db(db)
    lid, _ = crm.upsert_lead({"source": "linkedin", "external_id": "u1", "name": "A"}, db)
    crm.mark_contacted(lid, db)
    crm.log_message(lid, "linkedin", "outbound", "sent first", status="sent", path=db)
    crm.log_message(lid, "linkedin", "outbound", "a draft", status="draft", path=db)
    # The draft (no sent_at) must be ignored; cadence keys off the last SENT touch.
    due = sequence.due_followups(now=_now(5), gap_days=3, max_steps=3, path=db)
    assert len(due) == 1 and due[0]["next_step"] == 1  # next after the sent step 0, not the draft


# --- #3 reply matching by external_id alone (channel string unreliable) ---

def test_find_lead_by_external_id_alone(tmp_path):
    db = str(tmp_path / "t.sqlite")
    crm.init_db(db)
    crm.upsert_lead({"source": "linkedin", "external_id": "li-123", "name": "Jane"}, db)
    # No source given (inbound channel unknown) — still matches on a UNIQUE external_id.
    assert crm.find_lead_by(external_id="li-123", path=db)["name"] == "Jane"
    assert crm.find_lead_by(external_id="nope", path=db) is None


def test_find_lead_by_ambiguous_external_id_does_not_guess(tmp_path):
    db = str(tmp_path / "t.sqlite")
    crm.init_db(db)
    # Same external_id across two sources (id-namespace collision) → must NOT cross-attribute.
    crm.upsert_lead({"source": "linkedin", "external_id": "12345", "name": "LI Person"}, db)
    crm.upsert_lead({"source": "twitter", "external_id": "12345", "name": "X Person"}, db)
    assert crm.find_lead_by(external_id="12345", path=db) is None  # ambiguous → no guess
    # but with the source disambiguator it still resolves exactly:
    assert crm.find_lead_by(source="twitter", external_id="12345", path=db)["name"] == "X Person"


def test_sync_matches_linkedin_reply_with_unknown_channel(tmp_path, monkeypatch):
    db = str(tmp_path / "t.sqlite")
    crm.init_db(db)
    lid, _ = crm.upsert_lead({"source": "linkedin", "external_id": "li-9", "name": "Jane"}, db)
    crm.mark_contacted(lid, db)
    inbound = [{"external_message_id": "m1", "sender_id": "li-9", "sender_email": None,
                "channel": "MESSAGING", "body": "yes!"}]  # non-'linkedin' provider string
    monkeypatch.setattr(reply_handler, "_fetch_unipile_inbound", lambda: inbound)
    monkeypatch.setattr(reply_handler, "_fetch_x_inbound", lambda: [])
    res = reply_handler.sync(path=db)
    assert res["recorded"] == 1
    assert crm.get_lead(lid, db)["status"] == "replied"  # stop-on-reply engaged


# --- #2 duplicate-email update is handled, not a crash ---

def test_update_lead_duplicate_email_raises_valueerror(tmp_path):
    db = str(tmp_path / "t.sqlite")
    crm.init_db(db)
    a, _ = crm.upsert_lead({"source": "linkedin", "external_id": "a", "name": "A", "email": "x@acme.com"}, db)
    b, _ = crm.upsert_lead({"source": "linkedin", "external_id": "b", "name": "B"}, db)
    with pytest.raises(ValueError):
        crm.update_lead(b, {"email": "x@acme.com"}, db)


def test_enrich_lead_duplicate_email_clean(tmp_path, monkeypatch):
    db = str(tmp_path / "t.sqlite")
    crm.init_db(db)
    crm.upsert_lead({"source": "linkedin", "external_id": "a", "name": "A", "email": "ceo@acme.com"}, db)
    b, _ = crm.upsert_lead({"source": "linkedin", "external_id": "b", "name": "B", "website": "https://acme.com"}, db)
    monkeypatch.setattr(find_email, "require_env", lambda *a: ("k",))
    monkeypatch.setattr(find_email, "request",
        lambda *a, **k: type("R", (), {"json": lambda self: {"data": {"emails": [{"value": "ceo@acme.com", "confidence": 90}]}}})())
    res = find_email.enrich_lead(b, db)
    assert res["ok"] is False and "already assigned" in res["detail"]


# --- uninit-DB resilience ---

def test_due_followups_on_uninitialized_db(tmp_path):
    db = str(tmp_path / "fresh.sqlite")  # never init'd
    assert sequence.due_followups(path=db) == []


# --- new -> replied ---

def test_new_lead_can_be_marked_replied(tmp_path):
    db = str(tmp_path / "t.sqlite")
    crm.init_db(db)
    lid, _ = crm.upsert_lead({"source": "linkedin", "external_id": "u1", "name": "A"}, db)
    crm.mark_replied(lid, db)  # reply arrived before we ever marked contacted
    assert crm.get_lead(lid, db)["status"] == "replied"


# --- ICP path isolation via OUTREACHLY_ICP ---

def test_icp_path_env_override(tmp_path, monkeypatch):
    p = tmp_path / "myicp.json"
    monkeypatch.setenv("OUTREACHLY_ICP", str(p))
    valid = {"industries": ["x"], "titles": ["y"], "keywords": ["z"]}
    assert icp.save_icp(valid) == []  # writes to the override path, not data/icp.json
    assert p.exists()
    assert icp.load_icp() == valid
