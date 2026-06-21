"""Outreachly FastAPI app — REST surface over the script layer.

P0 exposes health + provider connectivity. Feature routes are added per phase.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.i18n import SUPPORTED_LOCALES
from app.integrations import ping_all

app = FastAPI(title="Outreachly API", version=__version__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "version": __version__, "locales": list(SUPPORTED_LOCALES)}


@app.get("/api/providers/ping")
def providers_ping() -> dict:
    """Connectivity sweep across all external providers."""
    results = ping_all()
    connected = sum(1 for r in results.values() if r["ok"])
    return {"connected": connected, "total": len(results), "providers": results}
