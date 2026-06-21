"""Central configuration & secret loading.

All external API keys are declared here. They are read from environment / `.env` only —
never hardcoded. A missing-but-required key raises a clear, named error at the point of use
(see `require()`), not a stack crash deep in an HTTP call.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root = two levels up from this file's package root (backend/app/core -> repo root).
REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "data"
DEFAULT_DB_PATH = DATA_DIR / "crm.sqlite"


class MissingConfigError(RuntimeError):
    """Raised when a required configuration value is absent."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Core ---
    app_env: str = Field(default="dev")
    default_locale: str = Field(default="en")  # "en" | "zh"
    db_path: str = Field(default=str(DEFAULT_DB_PATH))

    # --- LLM (ICP generation, copywriting) ---
    anthropic_api_key: str | None = Field(default=None)

    # --- Discovery / enrichment / outreach providers ---
    google_places_api_key: str | None = Field(default=None)
    unipile_dsn: str | None = Field(default=None)  # e.g. https://api{N}.unipile.com:{port}
    unipile_api_key: str | None = Field(default=None)
    x_bearer_token: str | None = Field(default=None)
    hunter_api_key: str | None = Field(default=None)
    neverbounce_api_key: str | None = Field(default=None)

    def require(self, *names: str) -> tuple[str, ...]:
        """Return the listed settings, raising MissingConfigError naming any that are unset.

        Usage: ``key, = settings.require("google_places_api_key")``
        """
        missing: list[str] = []
        values: list[str] = []
        for name in names:
            value = getattr(self, name, None)
            if not value:
                missing.append(name.upper())
            values.append(value)  # type: ignore[arg-type]
        if missing:
            raise MissingConfigError(
                "Missing required configuration: "
                + ", ".join(missing)
                + ". Add it to your .env (see .env.example)."
            )
        return tuple(values)


settings = Settings()
