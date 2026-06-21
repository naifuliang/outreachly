"""Optional local UI for Outreachly — launch only when you want it.

Serves the single-file web/index.html plus a tiny read-only JSON API over the CRM, using only
the Python standard library (no build step, no node_modules). Bundled inside the skill.

CLI:
  python scripts/serve_ui.py            # serve at http://127.0.0.1:8000
  python scripts/serve_ui.py --port 9000 --open
"""

from __future__ import annotations

import argparse
import json
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import crm
import find_email
import icp as icp_mod
import linkedin
import send_email
import twitter
import verify_email

WEB_DIR = Path(__file__).resolve().parents[1] / "web"
PROVIDER_PINGS = {
    "hunter": find_email.ping,
    "neverbounce": verify_email.ping,
    "unipile": send_email.ping,
    "linkedin": linkedin.ping,
    "twitter": twitter.ping,
}


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj) -> None:
        self._send(200, json.dumps(obj, ensure_ascii=False).encode("utf-8"),
                   "application/json; charset=utf-8")

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        try:
            if path in ("/", "/index.html"):
                html = (WEB_DIR / "index.html").read_bytes()
                self._send(200, html, "text/html; charset=utf-8")
            elif path == "/api/health":
                leads = crm.list_leads()
                self._json({"status": "ok", "leads": len(leads)})
            elif path == "/api/leads":
                self._json({"leads": crm.list_leads()})
            elif path == "/api/icp":
                self._json({"icp": icp_mod.load_icp()})
            elif path == "/api/funnel":
                self._json(crm.stats())
            elif path.startswith("/api/lead/") and path.endswith("/messages"):
                try:
                    lead_id = int(path.split("/")[3])
                    self._json({"messages": crm.list_messages(lead_id)})
                except (ValueError, IndexError):
                    self._send(400, b"bad lead id", "text/plain")
            elif path == "/api/providers":
                results = {}
                for name, fn in PROVIDER_PINGS.items():
                    try:
                        results[name] = fn()
                    except Exception as exc:
                        results[name] = {"provider": name, "ok": False, "detail": str(exc)}
                self._json({"providers": results})
            else:
                self._send(404, b"not found", "text/plain")
        except Exception as exc:  # keep the dev server alive
            self._json({"error": str(exc)})

    def do_POST(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b"{}"
            if path == "/api/icp":
                try:
                    payload = json.loads(raw.decode("utf-8"))
                except json.JSONDecodeError as exc:
                    self._json({"ok": False, "errors": [f"invalid JSON: {exc}"]})
                    return
                errors = icp_mod.save_icp(payload)
                self._json({"ok": not errors, "errors": errors})
            else:
                self._send(404, b"not found", "text/plain")
        except Exception as exc:
            self._json({"ok": False, "errors": [str(exc)]})

    def log_message(self, *args) -> None:  # quieter console
        return


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--open", action="store_true", help="Open a browser tab.")
    args = parser.parse_args()

    crm.init_db()  # ensure schema exists
    url = f"http://127.0.0.1:{args.port}"
    print(f"Outreachly UI → {url}  (Ctrl+C to stop)")
    if args.open:
        webbrowser.open(url)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
