"""Unipile integration (LinkedIn discovery + DM, Email send, unified inbox).

Docs: https://developer.unipile.com/
Auth: per-workspace DSN base URL (UNIPILE_DSN) + API key header X-API-KEY (UNIPILE_API_KEY).
"""

from __future__ import annotations

from app.core.api_client import ApiClient
from app.core.config import MissingConfigError, settings


def client() -> ApiClient:
    dsn, key = settings.require("unipile_dsn", "unipile_api_key")
    return ApiClient(
        "unipile",
        base_url=dsn.rstrip("/"),
        min_interval=0.05,
        headers={"X-API-KEY": key, "accept": "application/json"},
    )


def ping() -> dict:
    """List connected accounts as a connectivity probe. Returns {provider, ok, detail}."""
    try:
        c = client()
    except MissingConfigError as exc:
        return {"provider": "unipile", "ok": False, "detail": str(exc)}
    try:
        with c:
            resp = c.get("/api/v1/accounts")
        data = resp.json()
        n = len(data.get("items", data if isinstance(data, list) else []))
        return {"provider": "unipile", "ok": True, "detail": f"{n} account(s) connected"}
    except Exception as exc:
        return {"provider": "unipile", "ok": False, "detail": str(exc)}
