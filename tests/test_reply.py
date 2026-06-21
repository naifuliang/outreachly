"""Reply handling: record/sync/intent + stop-on-reply guard (providers mocked)."""

import crm
import linkedin
import reply_handler
import send_email


def _contacted_linkedin_lead(db, ext="u1"):
    lid, _ = crm.upsert_lead({"source": "linkedin", "external_id": ext, "name": "A"}, db)
    crm.mark_contacted(lid, db)  # new -> contacted
    return lid


def test_record_reply_marks_replied(tmp_path):
    db = str(tmp_path / "t.sqlite")
    crm.init_db(db)
    lid = _contacted_linkedin_lead(db)
    reply_handler.record_reply(lid, "linkedin", "sounds good", external_message_id="m1", path=db)
    assert crm.get_lead(lid, db)["status"] == "replied"
    msgs = crm.list_messages(lid, db)
    assert msgs[-1]["direction"] == "inbound" and msgs[-1]["body"] == "sounds good"


def test_set_intent(tmp_path):
    db = str(tmp_path / "t.sqlite")
    crm.init_db(db)
    lid = _contacted_linkedin_lead(db)
    reply_handler.record_reply(lid, "linkedin", "tell me more", external_message_id="m1", path=db)
    ok = reply_handler.set_intent(lid, "interested", db)
    assert ok["ok"]
    assert crm.latest_inbound(lid, db)["intent"] == "interested"
    assert reply_handler.set_intent(lid, "bogus", db)["ok"] is False


def test_sync_matches_dedups(tmp_path, monkeypatch):
    db = str(tmp_path / "t.sqlite")
    crm.init_db(db)
    lid = _contacted_linkedin_lead(db, ext="u1")

    inbound = [
        {"external_message_id": "m1", "sender_id": "u1", "sender_email": None,
         "channel": "linkedin", "body": "interested!"},
        {"external_message_id": "m2", "sender_id": "unknown", "sender_email": None,
         "channel": "linkedin", "body": "who matches this?"},  # no lead → skipped
    ]
    monkeypatch.setattr(reply_handler, "_fetch_unipile_inbound", lambda: inbound)
    monkeypatch.setattr(reply_handler, "_fetch_x_inbound", lambda: [])

    r1 = reply_handler.sync(path=db)
    assert r1["fetched"] == 2 and r1["recorded"] == 1 and r1["errors"] == []
    assert crm.get_lead(lid, db)["status"] == "replied"
    # second sync: m1 already seen → nothing new
    r2 = reply_handler.sync(path=db)
    assert r2["recorded"] == 0


def test_replied_lead_stops_sequence(tmp_path):
    db = str(tmp_path / "t.sqlite")
    crm.init_db(db)
    lid = _contacted_linkedin_lead(db)
    reply_handler.record_reply(lid, "linkedin", "yes", external_message_id="m1", path=db)
    # further sends are refused for a replied lead
    assert linkedin.dm(lid, "follow up", path=db)["ok"] is False
    crm.update_lead(lid, {"email": "a@acme.com", "email_status": "valid"}, db)
    res = send_email.send_email(lid, "s", "b", path=db)
    assert res["ok"] is False and "stopped" in res["detail"]
