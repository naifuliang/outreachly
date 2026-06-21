"""Discovery: X and LinkedIn search parse provider responses and upsert deduped leads.

External HTTP is mocked (no keys/network needed); live field-mapping is verified separately
once provider keys are connected.
"""

import crm
import linkedin
import twitter


class FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


TWEET_SEARCH = {
    "data": [
        {"id": "t1", "text": "love our espresso", "author_id": "u1"},
        {"id": "t2", "text": "new beans", "author_id": "u2"},
        {"id": "t3", "text": "more from u1", "author_id": "u1"},  # duplicate author
    ],
    "includes": {
        "users": [
            {"id": "u1", "name": "Blue Bottle", "username": "bluebottle",
             "description": "indie coffee", "location": "SF", "url": "https://bluebottle.com"},
            {"id": "u2", "name": "Ritual Coffee", "username": "ritual",
             "description": "roasters", "location": "SF"},
        ]
    },
}


def test_twitter_search_upserts_unique_authors(tmp_path, monkeypatch):
    db = str(tmp_path / "t.sqlite")
    crm.init_db(db)
    monkeypatch.setattr(twitter, "_auth_header", lambda: {"Authorization": "Bearer x"})
    monkeypatch.setattr(twitter, "request", lambda *a, **k: FakeResp(TWEET_SEARCH))

    res = twitter.search_twitter("coffee", 10, path=db)
    assert res["found"] == 2  # u1 deduped within the response
    assert res["created"] == 2
    leads = crm.list_leads(path=db)
    assert {l["name"] for l in leads} == {"Blue Bottle", "Ritual Coffee"}
    bb = next(l for l in leads if l["name"] == "Blue Bottle")
    assert bb["source"] == "twitter" and bb["domain"] == "bluebottle.com"


def test_twitter_search_dedups_across_calls(tmp_path, monkeypatch):
    db = str(tmp_path / "t.sqlite")
    crm.init_db(db)
    monkeypatch.setattr(twitter, "_auth_header", lambda: {"Authorization": "Bearer x"})
    monkeypatch.setattr(twitter, "request", lambda *a, **k: FakeResp(TWEET_SEARCH))
    twitter.search_twitter("coffee", 10, path=db)
    res2 = twitter.search_twitter("coffee", 10, path=db)
    assert res2["created"] == 0 and res2["updated"] == 2
    assert len(crm.list_leads(path=db)) == 2


ACCOUNTS = {"items": [{"id": "acc_li", "type": "LINKEDIN"}]}
LI_SEARCH = {
    "items": [
        {"id": "m1", "name": "Jane Doe", "headline": "Head of Marketing",
         "company": "FinCo", "location": "London"},
        {"first_name": "John", "last_name": "Roe", "member_id": "m2",
         "title": "VP Growth", "location": "Berlin"},
    ]
}


def _li_dispatch(provider, method, url, **kwargs):
    if url.endswith("/accounts"):
        return FakeResp(ACCOUNTS)
    return FakeResp(LI_SEARCH)


def test_linkedin_search_parses_and_upserts(tmp_path, monkeypatch):
    db = str(tmp_path / "t.sqlite")
    crm.init_db(db)
    monkeypatch.setattr(linkedin, "_base_and_headers", lambda: ("https://api.unipile", {"X-API-KEY": "k"}))
    monkeypatch.setattr(linkedin, "request", _li_dispatch)

    res = linkedin.search_linkedin("marketing fintech", 10, path=db)
    assert res["found"] == 2 and res["created"] == 2
    leads = {l["name"]: l for l in crm.list_leads(path=db)}
    assert "Jane Doe" in leads and leads["Jane Doe"]["title"] == "Head of Marketing"
    assert "John Roe" in leads  # first+last name fallback
    assert leads["John Roe"]["title"] == "VP Growth"
    assert all(l["source"] == "linkedin" for l in leads.values())
