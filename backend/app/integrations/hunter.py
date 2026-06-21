"""Hunter.io integration (email finding).

Docs: https://hunter.io/api-documentation/v2
Auth: API key (HUNTER_API_KEY).
"""

from __future__ import annotations

from app.core.api_client import ApiClient
from app.core.config import MissingConfigError, settings

BASE_URL = "https://api.hunter.io"


def client() -> ApiClient:
    return ApiClient("hunter", base_url=BASE_URL, min_interval=0.1)


def ping() -> dict:
    """Account-info call as a connectivity probe."""
    try:
        (key,) = settings.require("hunter_api_key")
    except MissingConfigError as exc:
        return {"provider": "hunter", "ok": False, "detail": str(exc)}
    try:
        with client() as c:
            resp = c.get("/v2/account", params={"api_key": key})
        data = resp.json().get("data", {})
        plan = data.get("plan_name", "unknown")
        return {"provider": "hunter", "ok": True, "detail": f"plan={plan}"}
    except Exception as exc:
        return {"provider": "hunter", "ok": False, "detail": str(exc)}
