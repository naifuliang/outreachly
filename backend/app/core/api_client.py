"""Unified external-API client: timeout, retry with backoff, simple rate limiting,
and normalized errors.

All integrations (`app.integrations.*`) build on this so behavior is consistent and there are
no raw httpx calls scattered through the script layer (see CONTRIBUTING.md §4).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import httpx

from .errors import ApiError, RateLimitError


@dataclass
class RateLimiter:
    """Minimal token-bucket-ish limiter: at most `min_interval` seconds between calls."""

    min_interval: float = 0.0
    _last: float = field(default=0.0, repr=False)

    def wait(self, *, now: float | None = None) -> None:
        if self.min_interval <= 0:
            return
        current = time.monotonic() if now is None else now
        elapsed = current - self._last
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last = time.monotonic() if now is None else now


class ApiClient:
    """A thin httpx wrapper scoped to a single provider.

    Args:
        provider:   short provider id used in normalized errors.
        base_url:   provider base URL.
        timeout:    per-request timeout (seconds).
        max_retries: retry attempts for retriable failures (5xx / 429 / network).
        min_interval: minimum seconds between requests (basic rate limiting).
        headers:    default headers (e.g. auth).
    """

    def __init__(
        self,
        provider: str,
        base_url: str = "",
        *,
        timeout: float = 15.0,
        max_retries: int = 3,
        min_interval: float = 0.0,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.provider = provider
        self._limiter = RateLimiter(min_interval=min_interval)
        self._client = httpx.Client(
            base_url=base_url, timeout=timeout, headers=headers or {}
        )
        self.max_retries = max_retries

    def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        attempt = 0
        while True:
            attempt += 1
            self._limiter.wait()
            try:
                resp = self._client.request(method, url, **kwargs)
            except httpx.TimeoutException as exc:
                if attempt > self.max_retries:
                    raise ApiError(
                        self.provider, f"timeout after {attempt} attempts", retriable=True
                    ) from exc
                self._backoff(attempt)
                continue
            except httpx.HTTPError as exc:
                if attempt > self.max_retries:
                    raise ApiError(self.provider, f"network error: {exc}", retriable=True) from exc
                self._backoff(attempt)
                continue

            if resp.status_code == 429:
                if attempt > self.max_retries:
                    raise RateLimitError(self.provider)
                self._backoff(attempt, resp=resp)
                continue
            if 500 <= resp.status_code < 600:
                if attempt > self.max_retries:
                    raise ApiError(
                        self.provider,
                        f"server error: {_short_body(resp)}",
                        status=resp.status_code,
                        retriable=True,
                    )
                self._backoff(attempt)
                continue
            if resp.status_code >= 400:
                raise ApiError(
                    self.provider,
                    f"client error: {_short_body(resp)}",
                    status=resp.status_code,
                    retriable=False,
                )
            return resp

    def get(self, url: str, **kwargs) -> httpx.Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs) -> httpx.Response:
        return self.request("POST", url, **kwargs)

    @staticmethod
    def _backoff(attempt: int, *, resp: httpx.Response | None = None) -> None:
        # Honor Retry-After when present, else exponential backoff capped at 8s.
        if resp is not None:
            retry_after = resp.headers.get("Retry-After")
            if retry_after and retry_after.isdigit():
                time.sleep(min(int(retry_after), 8))
                return
        time.sleep(min(2 ** (attempt - 1), 8))

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "ApiClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


def _short_body(resp: httpx.Response, limit: int = 200) -> str:
    try:
        text = resp.text
    except Exception:  # pragma: no cover - defensive
        return "<unreadable body>"
    return text[:limit].replace("\n", " ")
