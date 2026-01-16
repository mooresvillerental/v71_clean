#!/usr/bin/env python3
import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from datetime import datetime

HOST = "127.0.0.1"
PORT = 8080

STATE_PATH = os.path.expanduser("~/v70_app_data/state.json")
UI_DIR = os.path.join(os.path.dirname(__file__), "..", "ui")


def read_state():
    try:
        with open(STATE_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return None


def latest_signal_from_state(state):
    if not state:
        return {}

    decision = state.get("decision", {}) or {}
    primary = state.get("primary", {}) or {}

    return {
        "action": decision.get("action"),
        "reason": decision.get("reason"),
        "symbol": primary.get("symbol"),
        "price": primary.get("price"),
        "ts": state.get("ts"),
    }


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        state = read_state()

        # ---------------- HEALTH ----------------
        if path == "/health":
            ok = state is not None
            self._send_json(
                200,
                {
                    "ok": ok,
                    "state_path": STATE_PATH,
                    "note": "state.json readable" if ok else "state.json missing/unreadable",
                },
            )
            return

        # ---------------- UI FILES ----------------
        if path == "/" or path.endswith(".html"):
            target = os.path.join(UI_DIR, "index.html")
        else:
            target = os.path.join(UI_DIR, path.lstrip("/"))

        if os.path.isfile(target):
            try:
                if target.endswith(".html"):
                    ct = "text/html"
                elif target.endswith(".js"):
                    ct = "application/javascript"
                elif target.endswith(".css"):
                    ct = "text/css"
                elif target.endswith(".png"):
                    ct = "image/png"
                elif target.endswith(".jpg") or target.endswith(".jpeg"):
                    ct = "image/jpeg"
                elif target.endswith(".svg"):
                    ct = "image/svg+xml"
                else:
                    ct = "application/octet-stream"

                with open(target, "rb") as f:
                    data = f.read()

                self.send_response(200)
                self.send_header("Content-Type", ct)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            except Exception as e:
                self._send_json(500, {"ok": False, "error": "ui read failed", "detail": str(e)})
                return

        # ---------------- API ----------------
        if state is None:
            self._send_json(503, {"ok": False, "error": "state.json missing/unreadable"})
            return

        if path == "/decision":
            self._send_json(200, {"ok": True, "decision": state.get("decision", {})})
            return

        if path == "/signal":
            raw = latest_signal_from_state(state) or {}
            sig = {
                "action": raw.get("action") or "HOLD",
                "reason": raw.get("reason") or "NO_SIGNAL",
                "symbol": raw.get("symbol") or "UNKNOWN",
                "price": raw.get("price"),
                "ts": raw.get("ts"),
            }
            self._send_json(200, {"ok": True, "signal": sig})
            return

        # ---------------- NOT FOUND ----------------
        self._send_json(
            404,
            {
                "ok": False,
                "error": "not found",
                "paths": ["/health", "/decision", "/signal"],
            },
        )


def main():
    print(f"API server listening on http://{HOST}:{PORT}")
    print("Endpoints: /health /decision /signal")
    httpd = HTTPServer((HOST, PORT), Handler)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
