"""External provider integrations, each exposing a `ping()` connectivity check.

`ping_all()` is used by P0 acceptance and the `python -m app.integrations` CLI.
"""

from __future__ import annotations

from . import hunter, neverbounce, places, unipile, x_api

PROVIDERS = {
    "places": places.ping,
    "unipile": unipile.ping,
    "x": x_api.ping,
    "hunter": hunter.ping,
    "neverbounce": neverbounce.ping,
}


def ping_all() -> dict[str, dict]:
    """Ping every provider; never raises. Returns {provider: {ok, detail}}."""
    results: dict[str, dict] = {}
    for name, fn in PROVIDERS.items():
        try:
            results[name] = fn()
        except Exception as exc:  # defensive: a ping must never crash the sweep
            results[name] = {"provider": name, "ok": False, "detail": f"unexpected: {exc}"}
    return results


def _main() -> int:
    results = ping_all()
    ok = 0
    for name, r in results.items():
        mark = "OK " if r["ok"] else "FAIL"
        if r["ok"]:
            ok += 1
        print(f"[{mark}] {name:11s} {r['detail']}")
    print(f"\n{ok}/{len(results)} providers connected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
