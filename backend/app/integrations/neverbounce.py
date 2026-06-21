"""NeverBounce integration (email verification).

Docs: https://developers.neverbounce.com/
Auth: API key (NEVERBOUNCE_API_KEY).
"""

from __future__ import annotations

from app.core.api_client import ApiClient
from app.core.config import MissingConfigError, settings

BASE_URL = "https://api.neverbounce.com"


def client() -> ApiClient:
    return ApiClient("neverbounce", base_url=BASE_URL, min_interval=0.1)


def ping() -> dict:
    """Account-info call as a connectivity probe."""
    try:
        (key,) = settings.require("neverbounce_api_key")
    except MissingConfigError as exc:
        return {"provider": "neverbounce", "ok": False, "detail": str(exc)}
    try:
        with client() as c:
            resp = c.get("/v4/account/info", params={"key": key})
        data = resp.json()
        if data.get("status") == "success":
            return {"provider": "neverbounce", "ok": True, "detail": "account ok"}
        return {"provider": "neverbounce", "ok": False, "detail": str(data)[:120]}
    except Exception as exc:
        return {"provider": "neverbounce", "ok": False, "detail": str(exc)}
