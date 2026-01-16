#!/usr/bin/env python3
import json
import os
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

# -----------------------------
# Paths (uses your existing v69_app_data)
# -----------------------------
DATA_DIR = os.path.expanduser("~/v69_app_data")
STATE_PATH = os.path.join(DATA_DIR, "state.json")
CTRL_PATH  = os.path.join(DATA_DIR, "app_control.json")

# UI files live here:
UI_DIR = os.path.join(os.path.dirname(__file__), "..", "ui")
UI_DIR = os.path.abspath(UI_DIR)

HOST = "0.0.0.0"
PORT = 8080


def _read_json(path: str):
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return None


def latest_signal_from_state():
    state = _read_json(STATE_PATH)
    if not isinstance(state, dict):
        return {"status": "NO_STATE", "path": STATE_PATH}

    decision = state.get("decision", {}) if isinstance(state.get("decision", {}), dict) else {}
    action = decision.get("action")
    reason = decision.get("reason")

    # Only treat BUY/SELL as signals
    if action not in ("BUY", "SELL"):
        return {
            "status": "NO_SIGNAL",
            "ts": state.get("ts"),
            "action": action,
            "reason": reason,
        }

    primary = state.get("primary", {}) if isinstance(state.get("primary", {}), dict) else {}
    return {
        "status": "SIGNAL",
        "ts": state.get("ts"),
        "action": action,
        "reason": reason,
        "symbol": primary.get("symbol"),
        "price": primary.get("price"),
        "rsi": primary.get("rsi"),
        "paper_enforced": state.get("paper_enforced"),
        "cash_usd": state.get("cash_usd"),
        "holdings": state.get("holdings"),
    }


def status_from_control_and_state():
    ctrl = _read_json(CTRL_PATH)
    state = _read_json(STATE_PATH)

    scan = (ctrl.get("scan", {}) if isinstance(ctrl, dict) else {}) if ctrl else {}
    ui   = (ctrl.get("ui", {}) if isinstance(ctrl, dict) else {}) if ctrl else {}
    fees = (ctrl.get("fees", {}) if isinstance(ctrl, dict) else {}) if ctrl else {}
    bals = (ctrl.get("balances", {}) if isinstance(ctrl, dict) else {}) if ctrl else {}

    platform = (ctrl.get("platform") if isinstance(ctrl, dict) else None) if ctrl else None
    primary_symbol = scan.get("primary_symbol")

    paper_enforced = None
    if isinstance(state, dict):
        paper_enforced = state.get("paper_enforced")

    return {
        "status": "OK",
        "paths": {"ctrl": CTRL_PATH, "state": STATE_PATH},
        "platform": platform,
        "primary_symbol": primary_symbol,
        "ui_mode": ui.get("mode"),
        "fees": {
            "safety_multiplier": fees.get("safety_multiplier"),
            "close_call_ratio": fees.get("close_call_ratio"),
        },
        "balances": {
            "cash_usd": bals.get("cash_usd"),
            "btc": bals.get("btc"),  # key still named "btc" in ctrl.json today
        },
        "paper_enforced": paper_enforced,
        "ts": time.strftime("%Y-%m-%d %I:%M:%S %p"),
    }


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, obj, code=200):
        data = json.dumps(obj, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def _send_file(self, path, content_type="text/html; charset=utf-8"):
        if not os.path.exists(path):
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not found")
            return

        with open(path, "rb") as f:
            data = f.read()

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        p = urlparse(self.path).path

        # API endpoints
        if p == "/api/signal/latest":
            return self._send_json(latest_signal_from_state())
        if p == "/api/status":
            return self._send_json(status_from_control_and_state())

        # UI
        if p == "/" or p == "/index.html":
            return self._send_file(os.path.join(UI_DIR, "index.html"), "text/html; charset=utf-8")

        # Static assets under /ui/...
        if p.startswith("/ui/"):
            rel = p[len("/ui/"):]
            fs = os.path.join(UI_DIR, rel)
            # minimal content types
            if fs.endswith(".js"):
                return self._send_file(fs, "application/javascript; charset=utf-8")
            if fs.endswith(".css"):
                return self._send_file(fs, "text/css; charset=utf-8")
            if fs.endswith(".png"):
                return self._send_file(fs, "image/png")
            if fs.endswith(".jpg") or fs.endswith(".jpeg"):
                return self._send_file(fs, "image/jpeg")
            if fs.endswith(".svg"):
                return self._send_file(fs, "image/svg+xml")
            return self._send_file(fs, "application/octet-stream")

        # fallback
        self.send_response(404)
        self.end_headers()
        self.wfile.write(b"Not found")


def main():
    print(f"V70 Host (Mode-Aware) serving UI from: {UI_DIR}")
    print(f"Reading CTRL:  {CTRL_PATH}")
    print(f"Reading STATE: {STATE_PATH}")
    print(f"Listening on http://127.0.0.1:{PORT}  (LAN: http://{HOST}:{PORT})")
    httpd = HTTPServer((HOST, PORT), Handler)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
