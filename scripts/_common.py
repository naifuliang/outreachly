"""Shared helpers for Outreachly skill scripts.

Deliberately tiny: a zero-dependency `.env` loader, a clear `require_env`, a thin httpx
wrapper (timeout + retry + normalized error), and the SQLite path/connection. Keeping this
small is the point — the skill stays simple and importable.
"""

from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = REPO_ROOT / "data" / "crm.sqlite"

_ENV_LOADED = False


class ConfigError(RuntimeError):
    """A required env var is missing — message names which one."""


class ApiError(RuntimeError):
    """Normalized external-API failure: provider + message (+ optional status)."""

    def __init__(self, provider: str, message: str, status: int | None = None):
        self.provider = provider
        self.status = status
        super().__init__(f"[{provider}] {message}" + (f" (HTTP {status})" if status else ""))


def load_env() -> None:
    """Load REPO_ROOT/.env into os.environ once (does not override existing vars)."""
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    env_path = REPO_ROOT / ".env"
    if env_path.exists():
        for raw in env_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
    _ENV_LOADED = True


def require_env(*names: str) -> tuple[str, ...]:
    """Return the env values, raising ConfigError naming any that are unset."""
    load_env()
    missing, values = [], []
    for name in names:
        val = os.environ.get(name)
        if not val:
            missing.append(name)
        values.append(val)
    if missing:
        raise ConfigError(
            "Missing required env var(s): "
            + ", ".join(missing)
            + ". Add them to .env (see .env.example)."
        )
    return tuple(values)  # type: ignore[return-value]


def request(
    provider: str,
    method: str,
    url: str,
    *,
    timeout: float = 15.0,
    max_retries: int = 2,
    use_proxy: bool = True,
    **kwargs,
):
    """Thin httpx request with retry on 429/5xx/network and normalized ApiError.

    Imported lazily so scripts that never hit the network don't require httpx.

    `use_proxy` maps to httpx `trust_env`: when True (default) the environment proxy is honored
    (needed for region-blocked APIs like X); set False to connect directly — required for
    providers on non-standard ports a CONNECT proxy can't tunnel (e.g. Unipile's DSN port).
    """
    import httpx

    attempt = 0
    while True:
        attempt += 1
        try:
            resp = httpx.request(method, url, timeout=timeout, trust_env=use_proxy, **kwargs)
        except httpx.HTTPError as exc:
            if attempt > max_retries:
                raise ApiError(provider, f"network error: {exc}") from exc
            time.sleep(min(2 ** (attempt - 1), 8))
            continue
        if resp.status_code == 429 or 500 <= resp.status_code < 600:
            if attempt > max_retries:
                raise ApiError(provider, f"server/rate error: {resp.text[:160]}", resp.status_code)
            time.sleep(min(2 ** (attempt - 1), 8))
            continue
        if resp.status_code >= 400:
            raise ApiError(provider, f"client error: {resp.text[:160]}", resp.status_code)
        return resp


def db_path() -> str:
    load_env()
    return os.environ.get("OUTREACHLY_DB") or str(DEFAULT_DB)


def connect(path: str | None = None) -> sqlite3.Connection:
    p = Path(path or db_path())
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(p)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn
