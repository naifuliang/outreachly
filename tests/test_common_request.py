"""Coverage for _common.request (retry/normalize) and load_env — previously untested core."""

import httpx
import pytest

import _common
from _common import ApiError


class Resp:
    def __init__(self, status, body="", payload=None):
        self.status_code = status
        self.text = body
        self._payload = payload

    def json(self):
        return self._payload


def _seq(monkeypatch, responses):
    """Make httpx.request return/raise the given items in order."""
    calls = {"n": 0}

    def fake(*a, **k):
        i = min(calls["n"], len(responses) - 1)
        calls["n"] += 1
        item = responses[i]
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(httpx, "request", fake)
    monkeypatch.setattr(_common.time, "sleep", lambda *_: None)  # no real backoff
    return calls


def test_request_retries_5xx_then_succeeds(monkeypatch):
    calls = _seq(monkeypatch, [Resp(503, "busy"), Resp(503, "busy"), Resp(200, payload={"ok": 1})])
    resp = _common.request("t", "GET", "https://x", max_retries=2)
    assert resp.status_code == 200 and calls["n"] == 3


def test_request_4xx_raises_apierror_with_status(monkeypatch):
    _seq(monkeypatch, [Resp(404, "nope")])
    with pytest.raises(ApiError) as exc:
        _common.request("t", "GET", "https://x")
    assert exc.value.status == 404 and "t" in str(exc.value)


def test_request_429_raises_after_retries(monkeypatch):
    _seq(monkeypatch, [Resp(429, "slow"), Resp(429, "slow"), Resp(429, "slow")])
    with pytest.raises(ApiError):
        _common.request("t", "GET", "https://x", max_retries=1)


def test_request_network_error_normalized(monkeypatch):
    _seq(monkeypatch, [httpx.ConnectError("boom"), httpx.ConnectError("boom")])
    with pytest.raises(ApiError) as exc:
        _common.request("t", "GET", "https://x", max_retries=1)
    assert "network" in str(exc.value).lower()


def test_request_success_passes_through(monkeypatch):
    _seq(monkeypatch, [Resp(200, payload={"hi": True})])
    assert _common.request("t", "GET", "https://x").json() == {"hi": True}


def test_load_env_parses_and_does_not_override(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text('# comment\nFOO="bar"\nBAZ=qux\nPRESET=fromfile\n', encoding="utf-8")
    monkeypatch.setattr(_common, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(_common, "_ENV_LOADED", False)
    monkeypatch.setenv("PRESET", "fromenv")  # pre-existing must win
    monkeypatch.delenv("FOO", raising=False)
    monkeypatch.delenv("BAZ", raising=False)
    _common.load_env()
    import os
    assert os.environ["FOO"] == "bar"   # quotes stripped
    assert os.environ["BAZ"] == "qux"
    assert os.environ["PRESET"] == "fromenv"  # not overridden
