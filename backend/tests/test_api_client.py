"""P0: unified API client retries retriable failures and normalizes errors."""

import httpx
import pytest

from app.core.api_client import ApiClient
from app.core.errors import ApiError, RateLimitError


def _client_with_transport(handler, **kwargs) -> ApiClient:
    c = ApiClient("test", base_url="https://example.test", max_retries=2, **kwargs)
    c._client = httpx.Client(transport=httpx.MockTransport(handler), base_url="https://example.test")
    return c


def test_client_error_4xx_is_not_retried_and_normalized():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(404, text="nope")

    c = _client_with_transport(handler)
    with pytest.raises(ApiError) as exc:
        c.get("/x")
    assert exc.value.status == 404
    assert exc.value.retriable is False
    assert calls["n"] == 1  # no retry on 4xx


def test_server_error_5xx_is_retried_then_raises():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(503, text="busy")

    c = _client_with_transport(handler)
    with pytest.raises(ApiError) as exc:
        c.get("/x")
    assert exc.value.retriable is True
    assert calls["n"] == 3  # 1 try + 2 retries


def test_rate_limit_raises_ratelimit_error():
    def handler(request):
        return httpx.Response(429, text="slow down")

    c = _client_with_transport(handler)
    with pytest.raises(RateLimitError):
        c.get("/x")


def test_success_returns_response():
    def handler(request):
        return httpx.Response(200, json={"ok": True})

    c = _client_with_transport(handler)
    resp = c.get("/x")
    assert resp.json() == {"ok": True}
