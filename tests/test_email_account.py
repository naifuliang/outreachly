"""Email-account detection: pick the mailbox (Gmail=GOOGLE_OAUTH), never LinkedIn."""

import send_email


class FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def _accounts(*items):
    return FakeResp({"items": list(items)})


def test_picks_gmail_google_oauth(monkeypatch):
    monkeypatch.setattr(send_email, "request",
        lambda *a, **k: _accounts({"id": "li", "type": "LINKEDIN"},
                                  {"id": "g1", "type": "GOOGLE_OAUTH"}))
    assert send_email._email_account_id("b", {}) == "g1"


def test_picks_outlook(monkeypatch):
    monkeypatch.setattr(send_email, "request",
        lambda *a, **k: _accounts({"id": "o1", "type": "MICROSOFT"}))
    assert send_email._email_account_id("b", {}) == "o1"


def test_no_email_account_returns_none_not_linkedin(monkeypatch):
    # Only a LinkedIn account connected → must NOT return it for email.
    monkeypatch.setattr(send_email, "request",
        lambda *a, **k: _accounts({"id": "li", "type": "LINKEDIN"}))
    assert send_email._email_account_id("b", {}) is None


def test_env_override(monkeypatch):
    monkeypatch.setenv("UNIPILE_EMAIL_ACCOUNT_ID", "forced")
    assert send_email._email_account_id("b", {}) == "forced"
