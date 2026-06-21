"""Normalized error types shared across the script & integration layers.

Every external call funnels failures into these, so callers never have to special-case
provider-specific exception classes.
"""

from __future__ import annotations


class OutreachlyError(Exception):
    """Base class for all application errors."""


class ApiError(OutreachlyError):
    """A normalized external-API failure.

    Attributes:
        provider: short provider id, e.g. "places", "unipile", "x", "hunter".
        status:   HTTP status code if available, else None.
        message:  human-readable summary.
        retriable: whether a retry could plausibly succeed.
    """

    def __init__(
        self,
        provider: str,
        message: str,
        *,
        status: int | None = None,
        retriable: bool = False,
    ) -> None:
        self.provider = provider
        self.status = status
        self.retriable = retriable
        super().__init__(f"[{provider}] {message}" + (f" (HTTP {status})" if status else ""))


class RateLimitError(ApiError):
    """429 / provider rate limit. Always retriable."""

    def __init__(self, provider: str, message: str = "rate limited", *, status: int | None = 429):
        super().__init__(provider, message, status=status, retriable=True)
