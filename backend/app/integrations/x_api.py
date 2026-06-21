"""X (Twitter) API v2 integration (discovery + DM).

Docs: https://docs.x.com/x-api
Auth: App Bearer Token (X_BEARER_TOKEN) for read/search; DM sending additionally requires
user-context OAuth (wired in P5).
"""

from __future__ import annotations

from app.core.api_client import ApiClient
from app.core.config import MissingConfigError, settings

BASE_URL = "https://api.twitter.com"


def client() -> ApiClient:
    (token,) = settings.require("x_bearer_token")
    return ApiClient(
        "x",
        base_url=BASE_URL,
        min_interval=0.1,
        headers={"Authorization": f"Bearer {token}"},
    )


def ping() -> dict:
    """Resolve a known username as an app-bearer connectivity probe."""
    try:
        c = client()
    except MissingConfigError as exc:
        return {"provider": "x", "ok": False, "detail": str(exc)}
    try:
        with c:
            resp = c.get("/2/users/by/username/X")
        data = resp.json()
        if "data" in data:
            return {"provider": "x", "ok": True, "detail": f"resolved @{data['data'].get('username')}"}
        return {"provider": "x", "ok": False, "detail": str(data)[:120]}
    except Exception as exc:
        return {"provider": "x", "ok": False, "detail": str(exc)}
