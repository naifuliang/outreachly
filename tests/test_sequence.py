"""Follow-up scheduler: due detection by cadence, exhaustion, stop-on-reply; step recording."""

from datetime import datetime, timedelta, timezone

import crm
import send_email
import sequence


def _contacted_with_touch(db, step=0, ext="u1"):
    lid, _ = crm.upsert_lead({"source": "linkedin", "external_id": ext, "name": "A"}, db)
    crm.mark_contacted(lid, db)
    crm.log_message(lid, "linkedin", "outbound", "touch", sequence_step=step, status="sent", path=db)
    return lid


def test_due_after_gap(tmp_path):
    db = str(tmp_path / "t.sqlite")
    crm.init_db(db)
    lid = _contacted_with_touch(db, step=0)
    future = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=5)
    due = sequence.due_followups(now=future, gap_days=3, max_steps=3, path=db)
    assert len(due) == 1 and due[0]["lead_id"] == lid and due[0]["next_step"] == 1


def test_not_due_within_gap(tmp_path):
    db = str(tmp_path / "t.sqlite")
    crm.init_db(db)
    _contacted_with_touch(db, step=0)
    soon = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=1)
    assert sequence.due_followups(now=soon, gap_days=3, max_steps=3, path=db) == []


def test_sequence_exhausted(tmp_path):
    db = str(tmp_path / "t.sqlite")
    crm.init_db(db)
    _contacted_with_touch(db, step=2)  # last step in a 3-step sequence (0,1,2)
    future = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=30)
    assert sequence.due_followups(now=future, gap_days=3, max_steps=3, path=db) == []


def test_replied_excluded(tmp_path):
    db = str(tmp_path / "t.sqlite")
    crm.init_db(db)
    lid = _contacted_with_touch(db, step=0)
    crm.set_status(lid, "replied", db)  # reply stops the sequence
    future = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=10)
    assert sequence.due_followups(now=future, gap_days=3, max_steps=3, path=db) == []


def test_contacted_without_touch_excluded(tmp_path):
    db = str(tmp_path / "t.sqlite")
    crm.init_db(db)
    lid, _ = crm.upsert_lead({"source": "linkedin", "external_id": "u9", "name": "B"}, db)
    crm.mark_contacted(lid, db)  # status contacted but no outbound message logged
    future = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=10)
    assert sequence.due_followups(now=future, gap_days=3, max_steps=3, path=db) == []


def test_send_records_step(tmp_path):
    db = str(tmp_path / "t.sqlite")
    crm.init_db(db)
    lid, _ = crm.upsert_lead({"source": "linkedin", "external_id": "u1", "name": "A",
                              "email": "a@acme.com", "email_status": "valid"}, db)
    crm.mark_contacted(lid, db)
    # a draft records its step (but drafts don't drive cadence)
    send_email.send_email(lid, "Follow-up", "second touch", step=1, path=db)
    assert crm.last_outbound(lid, db)["sequence_step"] == 1
    # a real SENT step-1 touch advances the cadence to next_step 2
    crm.log_message(lid, "email", "outbound", "sent step1", status="sent", sequence_step=1, path=db)
    future = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=5)
    due = sequence.due_followups(now=future, gap_days=3, max_steps=3, path=db)
    assert due and due[0]["next_step"] == 2
