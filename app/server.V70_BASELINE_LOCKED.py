#!/usr/bin/env python3
import json, os, time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

HOST = os.environ.get("V70_HOST", "127.0.0.1")
PORT = int(os.environ.get("V70_PORT", "8080"))

HOME = os.path.expanduser("~")
DATA_DIR = os.environ.get("V70_DATA_DIR", os.path.join(HOME, "v70_app_data"))
STATE_PATH = os.environ.get("V70_STATE_PATH", os.path.join(DATA_DIR, "state.json"))
CONFIRM_PATH = os.environ.get("V70_CONFIRM_PATH", os.path.join(DATA_DIR, "confirm.json"))
UI_DIR = os.path.join(os.path.dirname(__file__), "..", "ui")
UI_DIR = os.path.abspath(UI_DIR)

def _read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def _write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=False)

def latest_signal_from_state(state: dict) -> dict:
    """
    Normalized output:
      { action, reason, symbol, price, ts }
    Supports the state.json you've been using:
      ts
      primary {symbol, price}
      decision {action, reason}
    """
    if not isinstance(state, dict):
        return {"action": "HOLD", "reason": "NO_STATE", "symbol": "UNKNOWN", "price": None, "ts": None}

    decision = state.get("decision") or {}
    primary = state.get("primary") or {}

    action = (decision.get("action") or "HOLD").upper()
    reason = decision.get("reason") or "NO_SIGNAL"
    symbol = primary.get("symbol") or "UNKNOWN"
    price = primary.get("price")
    ts = state.get("ts")

    # Normalize action
    if action not in ("BUY", "SELL", "HOLD"):
        action = "HOLD"
        reason = "BAD_ACTION"

    return {
        "action": action,
        "reason": reason,
        "symbol": symbol,
        "price": price,
        "ts": ts
    }

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        # quieter logs
        return

    def _send_json(self, code, obj):
        data = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_text(self, code, text, content_type="text/plain; charset=utf-8"):
        data = text.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _serve_file(self, target_path):
        # Basic static file server for ui/*
        if not os.path.isfile(target_path):
            self._send_json(404, {"ok": False, "error": "file not found"})
            return
        ext = os.path.splitext(target_path)[1].lower()
        ct = "application/octet-stream"
        if ext == ".html":
            ct = "text/html; charset=utf-8"
        elif ext == ".css":
            ct = "text/css; charset=utf-8"
        elif ext == ".js":
            ct = "application/javascript; charset=utf-8"
        elif ext == ".png":
            ct = "image/png"
        elif ext in (".jpg", ".jpeg"):
            ct = "image/jpeg"
        elif ext == ".svg":
            ct = "image/svg+xml"

        try:
            with open(target_path, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", ct)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            self._send_json(500, {"ok": False, "error": "ui file read failed", "detail": str(e)})

    def do_GET(self):
        path = urlparse(self.path).path

        # Root serves ui/index.html
        if path == "/" or path == "":
            return self._serve_file(os.path.join(UI_DIR, "index.html"))

        # Serve any /ui/* file
        if path.startswith("/ui/"):
            rel = path[len("/ui/"):]
            safe = os.path.normpath(rel).lstrip(os.sep)
            target = os.path.join(UI_DIR, safe)
            # block path traversal
            if not target.startswith(UI_DIR):
                return self._send_json(400, {"ok": False, "error": "bad path"})
            return self._serve_file(target)

        if path == "/health":
            state = _read_json(STATE_PATH)
            ok = state is not None
            return self._send_json(200, {
                "ok": True,
                "state_path": STATE_PATH,
                "note": "state.json readable" if ok else "state.json missing/unreadable"
            })

        state = _read_json(STATE_PATH)
        if state is None:
            return self._send_json(503, {"ok": False, "error": "state.json missing/unreadable", "state_path": STATE_PATH})

        if path == "/decision":
            return self._send_json(200, {"ok": True, "decision": state.get("decision", {})})

        if path == "/signal":
            sig = latest_signal_from_state(state)
            return self._send_json(200, {"ok": True, "signal": sig})

        if path == "/confirm/status":
            c = _read_json(CONFIRM_PATH)
            return self._send_json(200, {"ok": True, "confirm_path": CONFIRM_PATH, "confirm": c})

        return self._send_json(404, {"ok": False, "error": "not found", "paths": ["/health", "/decision", "/signal", "/confirm", "/confirm/status", "/ui/*", "/"]})

    def do_POST(self):
        path = urlparse(self.path).path

        if path != "/confirm":
            return self._send_json(404, {"ok": False, "error": "not found"})

        # Read body (JSON)
        try:
            n = int(self.headers.get("Content-Length", "0"))
        except Exception:
            n = 0
        body = self.rfile.read(n) if n > 0 else b""
        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except Exception:
            payload = {}

        requested = (payload.get("action") or "").upper().strip()
        note = (payload.get("note") or "").strip()

        if requested not in ("BUY", "SELL"):
            return self._send_json(400, {"ok": False, "error": "action must be BUY or SELL"})

        # Re-check current signal right now (Confirm + Re-check)
        state = _read_json(STATE_PATH)
        if state is None:
            return self._send_json(503, {"ok": False, "error": "state.json missing/unreadable", "state_path": STATE_PATH})

        sig = latest_signal_from_state(state)
        if sig.get("action") != requested:
            return self._send_json(409, {
                "ok": False,
                "error": "recheck_mismatch",
                "requested": requested,
                "current": sig
            })

        confirm = {
            "confirmed_at": time.strftime("%Y-%m-%d %I:%M:%S %p"),
            "action": requested,
            "signal": sig,
            "note": note
        }
        try:
            _write_json(CONFIRM_PATH, confirm)
        except Exception as e:
            return self._send_json(500, {"ok": False, "error": "write_failed", "detail": str(e), "confirm_path": CONFIRM_PATH})

        return self._send_json(200, {"ok": True, "confirm_path": CONFIRM_PATH, "confirm": confirm})

def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    print(f"API server listening on http://{HOST}:{PORT}")
    print("Endpoints: /health  /decision  /signal  /confirm  /confirm/status  /ui/*  /")
    httpd = HTTPServer((HOST, PORT), Handler)
    httpd.serve_forever()

if __name__ == "__main__":
    main()
