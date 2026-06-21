"""Google Places API integration (discovery).

Docs: https://developers.google.com/maps/documentation/places/web-service
Auth: API key (GOOGLE_PLACES_API_KEY).
"""

from __future__ import annotations

from app.core.api_client import ApiClient
from app.core.config import MissingConfigError, settings

BASE_URL = "https://maps.googleapis.com"


def client() -> ApiClient:
    return ApiClient("places", base_url=BASE_URL, min_interval=0.05)


def ping() -> dict:
    """Minimal Find-Place call. Returns {provider, ok, detail}."""
    try:
        (key,) = settings.require("google_places_api_key")
    except MissingConfigError as exc:
        return {"provider": "places", "ok": False, "detail": str(exc)}
    try:
        with client() as c:
            resp = c.get(
                "/maps/api/place/findplacefromtext/json",
                params={"input": "coffee", "inputtype": "textquery", "key": key},
            )
        status = resp.json().get("status", "UNKNOWN")
        if status in {"OK", "ZERO_RESULTS"}:
            return {"provider": "places", "ok": True, "detail": f"status={status}"}
        return {"provider": "places", "ok": False, "detail": f"status={status}"}
    except Exception as exc:
        return {"provider": "places", "ok": False, "detail": str(exc)}
