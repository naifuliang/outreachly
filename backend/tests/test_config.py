"""P0: missing required config raises a clear, named error (no stack crash)."""

import pytest

from app.core.config import MissingConfigError, Settings


def test_require_missing_names_the_env_var():
    s = Settings(google_places_api_key=None)
    with pytest.raises(MissingConfigError) as exc:
        s.require("google_places_api_key")
    assert "GOOGLE_PLACES_API_KEY" in str(exc.value)
    assert ".env" in str(exc.value)


def test_require_returns_values_when_present():
    s = Settings(google_places_api_key="abc", hunter_api_key="def")
    values = s.require("google_places_api_key", "hunter_api_key")
    assert values == ("abc", "def")


def test_require_reports_all_missing():
    s = Settings(google_places_api_key=None, hunter_api_key=None)
    with pytest.raises(MissingConfigError) as exc:
        s.require("google_places_api_key", "hunter_api_key")
    msg = str(exc.value)
    assert "GOOGLE_PLACES_API_KEY" in msg and "HUNTER_API_KEY" in msg
