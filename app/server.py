#!/usr/bin/env python3
import json, os, time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse



# === INTEL GUARDRAILS (stability + safety) ===
EZ_INTEL_GUARDRAILS = {
    # Network safety
    "HTTP_TIMEOUT_SEC": 6,
    "RSS_CACHE_TTL_SEC": 60,     # minimum cache window (prevents hammering)
    # Memory safety
    "TAPE_MAX_LEN": 20,          # hard cap to prevent memory creep
}
# === END INTEL GUARDRAILS ===

# === INTEL PROFILES (bounded presets) ===
EZ_INTEL_PROFILES = {
    # Most stable: fewer flips, micro trend off
    "conservative": {
        "TREND_UP_MULT": 1.0008,
        "TREND_DOWN_MULT": 0.9992,
        "MICRO_TREND_ENABLED": False,
    },
    # Default: balanced sensitivity
    "balanced": {
        "TREND_UP_MULT": 1.0004,
        "TREND_DOWN_MULT": 0.9996,
        "MICRO_TREND_ENABLED": True,
    },
    # Most responsive: flips easier, micro trend on
    "aggressive": {
        "TREND_UP_MULT": 1.0002,
        "TREND_DOWN_MULT": 0.9998,
        "MICRO_TREND_ENABLED": True,
    },
}

# Active profile (internal for now; later becomes user setting)
EZ_INTEL_ACTIVE_PROFILE = "balanced"
# === END INTEL PROFILES ===


# --- MARKET INTEL (Fortune-teller Phase 1) ---
_EZ_INTEL_CACHE = {"ts": 0, "headline": None}
_EZ_PRICE_TAPE = []

def _sentiment_label(text: str) -> str:
    t = (text or "").lower()
    pos = ["surge","rally","gain","gains","up","bull","bullish","approval","approved","win","wins","record","breakout","soar","positive","buy"]
    neg = ["crash","dump","loss","losses","down","bear","bearish","hack","lawsuit","ban","rejected","rejection","collapse","plunge","negative","sell"]
    score = 0
    for w in pos:
        if w in t: score += 1
    for w in neg:
        if w in t: score -= 1
    if score >= 2: return "POSITIVE"
    if score <= -2: return "NEGATIVE"
    return "NEUTRAL"

def _trend_from_tape(tape):
    try:
        t = list(tape or [])
        if len(t) >= 6:
            a = sum(t[-3:]) / 3.0
            b = sum(t[-6:-3]) / 3.0
            if a > b * EZ_INTEL_PROFILES[EZ_INTEL_ACTIVE_PROFILE]["TREND_UP_MULT"]: return "UP"
            if a < b * EZ_INTEL_PROFILES[EZ_INTEL_ACTIVE_PROFILE]["TREND_DOWN_MULT"]: return "DOWN"
    except Exception:
        pass
    return "FLAT"

def _get_rss_headline():
    # CoinDesk RSS with 60s cache
    import time as _t
    now = int(_t.time())
    cached = _EZ_INTEL_CACHE.get("headline")
    ts = int(_EZ_INTEL_CACHE.get("ts", 0) or 0)
    if cached and (now - ts) <= EZ_INTEL_GUARDRAILS["RSS_CACHE_TTL_SEC"]:
        return cached
    try:
        import urllib.request
        import xml.etree.ElementTree as ET
        rss_url = "https://www.coindesk.com/arc/outboundfeeds/rss/?outputType=xml"
        req = urllib.request.Request(rss_url, headers={"User-Agent":"EZTrader/1.0"})
        with urllib.request.urlopen(req, timeout=EZ_INTEL_GUARDRAILS["HTTP_TIMEOUT_SEC"]) as r:
            xml = r.read()
        root = ET.fromstring(xml)
        item = root.find(".//item")
        ttl = item.findtext("title") if item is not None else None
        if ttl:
            headline = ttl.strip()
            _EZ_INTEL_CACHE["headline"] = headline
            _EZ_INTEL_CACHE["ts"] = now
            return headline
    except Exception:
        pass
    return cached or "—"

def get_market_intel(tape):
    headline = _get_rss_headline()
    sent = _sentiment_label(headline)
    trend = _trend_from_tape(tape)
    if EZ_INTEL_PROFILES[EZ_INTEL_ACTIVE_PROFILE]["MICRO_TREND_ENABLED"]:

        # micro trend (last 3 ticks)
        micro = "FLAT"
        try:
            t = list(tape or [])
            if len(t) >= 3:
                if t[-1] > t[-2] > t[-3]:
                    micro = "UP"
                elif t[-1] < t[-2] < t[-3]:
                    micro = "DOWN"
        except Exception:
            pass

    out = {"headline": headline, "sentiment": sent, "trend": trend}
    if EZ_INTEL_PROFILES[EZ_INTEL_ACTIVE_PROFILE]["MICRO_TREND_ENABLED"]:
        out["micro_trend"] = micro
    return out
# --- END MARKET INTEL ---


from app.pnl import update_after_confirm

HOST = os.environ.get("V70_HOST", "127.0.0.1")
PORT = int(os.environ.get("V70_PORT", "8080"))

HOME = os.path.expanduser("~")

# APP data (v70): confirmations live here
APP_DATA_DIR = os.environ.get("V70_DATA_DIR", os.path.join(HOME, "v70_app_data"))
APP_STATE_PATH = os.environ.get("V70_APP_STATE_PATH", os.path.join(APP_DATA_DIR, "state.json"))
CONFIRM_PATH = os.environ.get("V70_CONFIRM_PATH", os.path.join(APP_DATA_DIR, "confirm.json"))
SETTINGS_PATH = os.environ.get("V70_SETTINGS_PATH", os.path.join(APP_DATA_DIR, "settings.json"))

# ENGINE data (v69): signals come from here (authoritative)
ENGINE_STATE_PATH = os.environ.get("V70_ENGINE_STATE_PATH", os.path.join(HOME, "v69_app_data", "state.json"))

UI_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ui"))

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


def _default_settings():
    # Safe defaults (can be edited later)
    return {
        "reco_mode": "percent",
        "reco_percent": 0.05,
        "fee_buffer_pct": 0.02,
        "fee_buffer_usd": 0.0,
        "updated_at": time.strftime("%Y-%m-%d %I:%M:%S %p")
    }

def apply_settings_patch(payload: dict, s: dict):
    """
    Validate + apply allowed settings keys. Returns (new_settings, changed_keys).
    Raises ValueError for invalid inputs.
    """
    if not isinstance(s, dict):
        s = {}
    if not isinstance(payload, dict):
        payload = {}

    allowed = {
        "reco_mode", "reco_percent",
        "fee_buffer_pct", "fee_buffer_usd",
        "min_trade_usd",
        "intel_profile",
    }

    out = dict(s)
    changed = {}

    # intel_profile (bounded presets)
    if payload.get("intel_profile") is not None:
        ip = str(payload.get("intel_profile")).strip().lower()
        if ip not in EZ_INTEL_PROFILES:
            raise ValueError("bad intel_profile")
        out["intel_profile"] = ip
        changed["intel_profile"] = ip

    # other allowed keys
    for k in allowed:
        if k == "intel_profile":
            continue
        if k in payload:
            out[k] = payload[k]
            changed[k] = payload[k]

    # stamp
    try:
        import time as _t
        out["updated_at"] = _t.strftime("%Y-%m-%d %I:%M:%S %p")
    except Exception:
        pass

    return out, changed


def _load_settings():
    s = _read_json(SETTINGS_PATH)
    if not isinstance(s, dict):
        s = _default_settings()
        _write_json(SETTINGS_PATH, s)
    # default minimum trade (USD)
    if "min_trade_usd" not in s:
        s["min_trade_usd"] = 25

        return s
    # fill any missing keys
    d = _default_settings()
    changed = False
    for k,v in d.items():
        if k not in s:
            s[k] = v
            changed = True
    if changed:
        s["updated_at"] = time.strftime("%Y-%m-%d %I:%M:%S %p")
        _write_json(SETTINGS_PATH, s)
    return s
def latest_signal_from_engine(engine_state: dict) -> dict:
    """Normalized signal contract:
      { action, reason, symbol, price, ts }
    Reads v69-style engine state:
      decision {action, reason}
      primary  {symbol, price}
      ts
    """
    if not isinstance(engine_state, dict):
        return {"action": "HOLD", "reason": "NO_ENGINE_STATE", "symbol": "UNKNOWN", "price": None, "ts": None}

    decision = engine_state.get("decision") or {}
    primary = engine_state.get("primary") or {}

    action = (decision.get("action") or "HOLD").upper()
    reason = decision.get("reason") or "NO_SIGNAL"
    symbol = primary.get("symbol") or "UNKNOWN"
    price = primary.get("price")
    ts = engine_state.get("ts")

    if action not in ("BUY", "SELL", "HOLD"):
        action = "HOLD"
        reason = "BAD_ACTION"

    return {"action": action, "reason": reason, "symbol": symbol, "price": price, "ts": ts}

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def _send_json(self, code, obj):
        data = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        try:
            self.wfile.write(data)
        except Exception:
            pass

    def _serve_file(self, target_path):
        if not os.path.isfile(target_path):
            return self._send_json(404, {"ok": False, "error": "file not found"})
        ext = os.path.splitext(target_path)[1].lower()
        ct = "application/octet-stream"
        if ext == ".html": ct = "text/html; charset=utf-8"
        elif ext == ".css": ct = "text/css; charset=utf-8"
        elif ext == ".js": ct = "application/javascript; charset=utf-8"
        elif ext == ".png": ct = "image/png"
        elif ext in (".jpg", ".jpeg"): ct = "image/jpeg"
        elif ext == ".svg": ct = "image/svg+xml"

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

        # UI
        if path == "/" or path == "":
            return self._serve_file(os.path.join(UI_DIR, "monitor.html"))

        if path == "/trade":
            return self._serve_file(os.path.join(UI_DIR, "trade.html"))
        if path.startswith("/ui/"):
            rel = path[len("/ui/"):]
            safe = os.path.normpath(rel).lstrip(os.sep)
            target = os.path.join(UI_DIR, safe)
            if not target.startswith(UI_DIR):
                return self._send_json(400, {"ok": False, "error": "bad path"})
            return self._serve_file(target)

        # load both layers
        engine = _read_json(ENGINE_STATE_PATH)
        appst  = _read_json(APP_STATE_PATH)

        if path == "/health":
            return self._send_json(200, {
                "ok": True,
                "engine_state_path": ENGINE_STATE_PATH,
                "engine_state_readable": bool(engine is not None),
                "app_state_path": APP_STATE_PATH,
                "app_state_readable": bool(appst is not None),
                "confirm_path": CONFIRM_PATH
            })

        if engine is None:
            return self._send_json(503, {"ok": False, "error": "engine state missing/unreadable", "engine_state_path": ENGINE_STATE_PATH})

        if path == "/decision":
            # --- PNL POST-CONFIRM (safe) ---
            try:
                _pnl_info = _pnl_update_after_confirm(
                    symbol=symbol,
                    action=action,
                    price=float(price),
                    pre_cash=float(_pnl_pre_cash),
                    pre_qty=float(_pnl_pre_qty),
                    pre_mtime=float(_pnl_pre_mtime),
                )
            except Exception as e:
                _pnl_info = {'ok': False, 'note': 'pnl_exception', 'detail': str(e)}
            # Attach pnl info if payload is a dict
            try:
                if isinstance({"ok": True, "decision": (engine.get("decision") or {})}, dict):
                    {"ok": True, "decision": (engine.get("decision") or {})}['pnl'] = _pnl_info
            except Exception:
                pass
            # --- END PNL POST-CONFIRM ---

            return self._send_json(200, {"ok": True, "decision": (engine.get("decision") or {})})

        if path == "/signal":
            sig = latest_signal_from_engine(engine)
            return self._send_json(200, {"ok": True, "signal": sig})

        if path == "/intel":
            # Fortune-teller Phase 1: headline + sentiment + trend
            global _EZ_PRICE_TAPE

            sig = latest_signal_from_engine(engine)
            lp = None

            try:
                # Live price (Coinbase spot, no API key)
                import urllib.request, json
                with urllib.request.urlopen(
                    "https://api.coinbase.com/v2/prices/BTC-USD/spot",
                    timeout=EZ_INTEL_GUARDRAILS["HTTP_TIMEOUT_SEC"]
                ) as r:
                    j = json.loads(r.read().decode("utf-8"))
                lp = float((j.get("data") or {}).get("amount") or 0) or None
            except Exception:
                lp = None

            if lp is None:
                lp = None  # stay None if Coinbase fetch fails

            try:
                if lp is not None:
                    _EZ_PRICE_TAPE.append(lp)
                    if len(_EZ_PRICE_TAPE) > EZ_INTEL_GUARDRAILS["TAPE_MAX_LEN"]:
                        _EZ_PRICE_TAPE = _EZ_PRICE_TAPE[-EZ_INTEL_GUARDRAILS["TAPE_MAX_LEN"]:]
            except Exception:
                pass

            info = get_market_intel(_EZ_PRICE_TAPE)
            return self._send_json(
                200,
                {
                    "ok": True,
                    "lp": lp,
                    "tape_len": len(_EZ_PRICE_TAPE),
                    **info
                }
            )

        if path == "/reco":
            # Recommended amount endpoint (authoritative engine-driven signal + balances)
            sig = latest_signal_from_engine(engine)
            action = (sig.get("action") or "HOLD").upper()
            symbol = sig.get("symbol") or "BTC-USD"
            price = sig.get("price")

            # Try multiple places for cash + BTC holdings (engine format varies across versions)
            cash = None
            for k in ("cash_usd", "usd", "cash"):
                if k in (engine or {}):
                    cash = engine.get(k)
                    break
            if cash is None:
                b = (engine or {}).get("balances") or {}
                cash = b.get("cash_usd", b.get("usd", 0.0))
            try:
                cash = float(cash or 0.0)
            except Exception:
                cash = 0.0

            holdings = (engine or {}).get("holdings") or {}
            btc_now = holdings.get(symbol, holdings.get("BTC-USD", holdings.get("BTC", 0.0)))
            if btc_now in (None, ""):
                b = (engine or {}).get("balances") or {}
                btc_now = b.get("btc", 0.0)
            try:
                btc_now = float(btc_now or 0.0)
            except Exception:
                btc_now = 0.0

            # If engine already provides a recommendation, honor it.
            recommended_usd = (engine or {}).get("recommended_usd")
            recommended_btc = (engine or {}).get("recommended_btc")

            # Flexible fallbacks for other legacy keys
            if recommended_usd is None:
                rec = (engine or {}).get("recommended") or (engine or {}).get("recommendation") or {}
                if isinstance(rec, dict):
                    recommended_usd = rec.get("usd", rec.get("recommended_usd"))
                    recommended_btc = rec.get("btc", rec.get("recommended_btc"))

            # Compute fallback if not provided:
            # BUY  -> 2% of cash (min $5, max cash)
            # SELL -> 2% of BTC holdings (converted to USD for display)
            try:
                px = float(price) if price is not None else None
            except Exception:
                px = None

            if action == "BUY":
                if recommended_usd is None:
                    amt = cash * 0.02
                    if cash > 0 and amt < 5:
                        amt = min(5.0, cash)
                    if amt > cash:
                        amt = cash
                    recommended_usd = round(max(0.0, amt), 2)
                # for BUY, recommended_btc can be derived if we have price
                if recommended_btc is None and px and px > 0 and recommended_usd:
                    recommended_btc = round(float(recommended_usd) / px, 8)

            elif action == "SELL":
                if recommended_btc is None:
                    btc_amt = btc_now * 0.02
                    recommended_btc = round(max(0.0, btc_amt), 8)
                if recommended_usd is None and px and px > 0 and recommended_btc:
                    recommended_usd = round(float(recommended_btc) * px, 2)

            else:
                # HOLD: show nothing
                recommended_usd = None
                recommended_btc = None

            return self._send_json(200, {
                "ok": True,
                "action": action,
                "symbol": symbol,
                "price": price,
                "recommended_usd": recommended_usd,

                "recommended_btc": recommended_btc
            })

        if path == "/confirm/status":
            c = _read_json(CONFIRM_PATH)
            return self._send_json(200, {"ok": True, "confirm_path": CONFIRM_PATH, "confirm": c})

        if path == "/settings":
            # allowed keys for POST /settings
            allowed = {
                "reco_mode", "reco_percent",
                "fee_buffer_pct", "fee_buffer_usd",
                "min_trade_usd",
                "intel_profile",
            }


            s = _load_settings()
            if isinstance(s, dict) and "intel_profile" not in s:
                s["intel_profile"] = EZ_INTEL_ACTIVE_PROFILE
            return self._send_json(200, {"ok": True, "settings_path": SETTINGS_PATH, "settings": s})

        return self._send_json(404, {"ok": False, "error": "not found", "paths": ["/health", "/decision", "/signal", "/confirm", "/confirm/status", "/ui/*", "/"]})

    def do_POST(self):
        path = urlparse(self.path).path
        if path not in ("/confirm", "/settings"):
            return self._send_json(404, {"ok": False, "error": "not found"})

        # body json
        try:
            n = int(self.headers.get("Content-Length", "0"))
        except Exception:
            n = 0
        body = self.rfile.read(n) if n > 0 else b""
        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except Exception:
            payload = {}

        if path == "/settings":
            try:
                s0 = _load_settings()
                s1, changed = apply_settings_patch(payload, s0)
                _write_json(SETTINGS_PATH, s1)

                # apply active profile live (default balanced)
                global EZ_INTEL_ACTIVE_PROFILE
                EZ_INTEL_ACTIVE_PROFILE = str(s1.get("intel_profile") or "balanced").strip().lower()
                if EZ_INTEL_ACTIVE_PROFILE not in EZ_INTEL_PROFILES:
                    EZ_INTEL_ACTIVE_PROFILE = "balanced"

                return self._send_json(200, {"ok": True, "settings_path": SETTINGS_PATH, "settings": s1, "changed": changed})
            except ValueError as e:
                return self._send_json(400, {"ok": False, "error": str(e)})
            except Exception as e:
                return self._send_json(500, {"ok": False, "error": "settings_post_failed", "detail": str(e)})

        requested = (payload.get("action") or "").upper().strip()
        note = (payload.get("note") or "").strip()

        if requested not in ("BUY", "SELL"):
            return self._send_json(400, {"ok": False, "error": "action must be BUY or SELL"})

        engine = _read_json(ENGINE_STATE_PATH)
        if engine is None:
            return self._send_json(503, {"ok": False, "error": "engine state missing/unreadable", "engine_state_path": ENGINE_STATE_PATH})

            sig = latest_signal_from_engine(engine)

        # Confirm + Re-check: only allow if engine still matches
        if sig.get("action") != requested:
            return self._send_json(409, {"ok": False, "error": "recheck_mismatch", "requested": requested, "current": sig})

        # --- PNL PRE-SNAPSHOT (safe) ---

        _pnl_pre_cash = 0.0

        _pnl_pre_qty = 0.0

        _pnl_pre_mtime = 0.0

        try:

            from pathlib import Path as _Path

            _app_path = _Path.home() / 'v69_app_data' / 'app_state.json'

            if _app_path.exists():

                _pnl_pre_mtime = _app_path.stat().st_mtime

                _st = _read_json(str(_app_path)) or {}

                _pnl_pre_cash = float(_st.get('cash_usd', 0.0))

                _h = (_st.get('holdings', {}) or {})

                _pnl_pre_qty = float(_h.get(symbol, 0.0))

        except Exception:

            pass

        # --- END PNL PRE-SNAPSHOT ---



        confirm = {
            "confirmed_at": time.strftime("%Y-%m-%d %I:%M:%S %p"),
            "action": requested,
            "signal": sig,
            "note": note
        }
        try:
            _write_json(CONFIRM_PATH, confirm)
            try:
                update_after_confirm(confirm)
            except Exception as _e:
                pass
        except Exception as e:
            return self._send_json(500, {"ok": False, "error": "write_failed", "detail": str(e), "confirm_path": CONFIRM_PATH})

        return self._send_json(200, {"ok": True, "confirm_path": CONFIRM_PATH, "confirm": confirm})

def main():
    os.makedirs(APP_DATA_DIR, exist_ok=True)
    httpd = HTTPServer((HOST, PORT), Handler)
    httpd.serve_forever()

if __name__ == "__main__":
    main()