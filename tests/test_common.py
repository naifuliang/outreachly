"""P0: env loading raises a clear, named error when a required var is missing."""

import os

import pytest

import _common
from _common import ConfigError, require_env


def test_require_env_names_missing(monkeypatch):
    monkeypatch.setattr(_common, "_ENV_LOADED", True)  # skip .env file read
    monkeypatch.delenv("GOOGLE_PLACES_API_KEY", raising=False)
    with pytest.raises(ConfigError) as exc:
        require_env("GOOGLE_PLACES_API_KEY")
    assert "GOOGLE_PLACES_API_KEY" in str(exc.value)
    assert ".env" in str(exc.value)


def test_require_env_returns_values(monkeypatch):
    monkeypatch.setattr(_common, "_ENV_LOADED", True)
    monkeypatch.setenv("HUNTER_API_KEY", "abc")
    assert require_env("HUNTER_API_KEY") == ("abc",)


def test_require_env_reports_all_missing(monkeypatch):
    monkeypatch.setattr(_common, "_ENV_LOADED", True)
    monkeypatch.delenv("UNIPILE_DSN", raising=False)
    monkeypatch.delenv("UNIPILE_API_KEY", raising=False)
    with pytest.raises(ConfigError) as exc:
        require_env("UNIPILE_DSN", "UNIPILE_API_KEY")
    msg = str(exc.value)
    assert "UNIPILE_DSN" in msg and "UNIPILE_API_KEY" in msg
