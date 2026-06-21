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
    monkeypatch.setattr(reply_handler, "_fetch_unipile_emails", lambda: [])
    monkeypatch.setattr(reply_handler, "_fetch_x_inbound", lambda: [])

    r1 = reply_handler.sync(path=db)
    assert r1["fetched"] == 2 and r1["recorded"] == 1 and r1["errors"] == []
    assert crm.get_lead(lid, db)["status"] == "replied"
    # second sync: m1 already seen → nothing new
    r2 = reply_handler.sync(path=db)
    assert r2["recorded"] == 0


class _Resp:
    def __init__(self, payload):
        self._p = payload

    def json(self):
        return self._p


ACCOUNTS = {"items": [{"id": "g1", "type": "GOOGLE_OAUTH"}, {"id": "li", "type": "LINKEDIN"}]}
EMAILS = {"items": [
    {"id": "e1", "role": "inbox", "from_attendee": {"identifier": "prospect@acme.com"},
     "body_plain": "Yes, interested!"},
    {"id": "e2", "role": "sent", "from_attendee": {"identifier": "me@me.com"},
     "body_plain": "my own sent mail"},  # outbound → must be skipped
]}


def test_fetch_unipile_emails_received_only(monkeypatch):
    monkeypatch.setenv("UNIPILE_DSN", "https://api.unipile")
    monkeypatch.setenv("UNIPILE_API_KEY", "k")

    def dispatch(provider, method, url, **kw):
        return _Resp(ACCOUNTS) if url.endswith("/accounts") else _Resp(EMAILS)

    monkeypatch.setattr(reply_handler, "request", dispatch)
    out = reply_handler._fetch_unipile_emails()
    assert len(out) == 1  # 'sent' skipped
    assert out[0]["sender_email"] == "prospect@acme.com" and out[0]["channel"] == "email"


def test_sync_records_email_reply_by_email(tmp_path, monkeypatch):
    db = str(tmp_path / "t.sqlite")
    crm.init_db(db)
    lid, _ = crm.upsert_lead({"source": "manual", "external_id": "p1", "name": "Prospect",
                              "email": "prospect@acme.com"}, db)
    crm.mark_contacted(lid, db)
    monkeypatch.setattr(reply_handler, "_fetch_unipile_inbound", lambda: [])
    monkeypatch.setattr(reply_handler, "_fetch_x_inbound", lambda: [])
    monkeypatch.setattr(reply_handler, "_fetch_unipile_emails", lambda: [
        {"external_message_id": "e1", "sender_id": None, "sender_email": "prospect@acme.com",
         "channel": "email", "body": "Yes!"}])
    res = reply_handler.sync(path=db)
    assert res["recorded"] == 1
    assert crm.get_lead(lid, db)["status"] == "replied"  # email reply stops the sequence


def test_sync_dedups_same_id_within_one_batch(tmp_path, monkeypatch):
    db = str(tmp_path / "t.sqlite")
    crm.init_db(db)
    lid, _ = crm.upsert_lead({"source": "manual", "external_id": "p1", "name": "P",
                              "email": "prospect@acme.com"}, db)
    crm.mark_contacted(lid, db)
    dup = {"external_message_id": "same-1", "sender_id": None, "sender_email": "prospect@acme.com",
           "channel": "email", "body": "yes"}
    monkeypatch.setattr(reply_handler, "_fetch_unipile_inbound", lambda: [])
    monkeypatch.setattr(reply_handler, "_fetch_x_inbound", lambda: [])
    monkeypatch.setattr(reply_handler, "_fetch_unipile_emails", lambda: [dup, dict(dup)])
    res = reply_handler.sync(path=db)
    assert res["recorded"] == 1  # same external_message_id within one batch → recorded once


def test_fetch_emails_skips_non_dict_items(monkeypatch):
    monkeypatch.setenv("UNIPILE_DSN", "https://api.unipile")
    monkeypatch.setenv("UNIPILE_API_KEY", "k")
    emails = {"items": ["garbage", {"id": "e1", "role": "inbox",
              "from_attendee": {"identifier": "p@acme.com"}, "body_plain": "hi"}]}

    def dispatch(provider, method, url, **kw):
        return _Resp({"items": [{"id": "g1", "type": "GOOGLE_OAUTH"}]}) if url.endswith("/accounts") else _Resp(emails)

    monkeypatch.setattr(reply_handler, "request", dispatch)
    out = reply_handler._fetch_unipile_emails()  # must not crash on the "garbage" string item
    assert len(out) == 1 and out[0]["sender_email"] == "p@acme.com"


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
