
# === EZ_CONFIRM_TRADE_V1 ===
_CONFIRM_LOCKS = {}

def _ez_json_read(handler):
    try:
        n = int(handler.headers.get("Content-Length","0") or "0")
    except Exception:
        n = 0
    raw = handler.rfile.read(n) if n > 0 else b""
    try:
        import json


        return json.loads(raw.decode("utf-8") or "{}")
    except Exception:
        return {}

def _ez_json_write(handler, obj, code=200):
    import json


    data = json.dumps(obj).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)

def _ez_load_state(path):
    import json


    try:
        return json.loads(Path(path).read_text())
    except Exception:
        return {}

def _ez_save_state(path, state):
    import json


    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(state, indent=2), encoding="utf-8")

def _ez_confirm_trade(state, evt):
    import time
    cid = evt.get("cid") or f"{evt.get('side')}:{evt.get('usd')}:{evt.get('price')}"
    now = time.time()
    last = _CONFIRM_LOCKS.get(cid)
    if last and now - last < 2.0:
        return {"ok": False, "error": "duplicate_confirm"}
    _CONFIRM_LOCKS[cid] = now


    side = str(evt.get("side","")).upper().strip()
    try:
        usd = float(evt.get("usd", 0) or 0)
    except Exception:
        usd = 0.0
    try:
        price = float(evt.get("price", 0) or 0)
    except Exception:
        price = 0.0

    rec = {
        "type": "TRADE",
        "side": side,
        "usd": usd,
        "price": price,
        "ts": int(time.time())
    }

    state.setdefault("history", []).append(rec)

    # balances are the source of truth
    bal = state.setdefault("balances", {})
    cash = float(bal.get("cash_usd", 0) or 0)
    btc  = float(bal.get("btc", 0) or 0)

    # Only apply math if we have a usable price and amount
    if usd > 0 and price > 0 and side in ("BUY","SELL"):
        btc_delta = usd / price
        if side == "BUY":
            cash = cash - usd
            btc  = btc + btc_delta
        else:  # SELL
            cash = cash + usd
            btc  = btc - btc_delta
            if btc < 0:  # safety clamp
                btc = 0.0

    bal["cash_usd"] = float(cash)
    bal["btc"] = float(btc)

    return rec

# === /EZ_CONFIRM_TRADE_V1 ===

from pathlib import Path
import urllib.parse as _EZU

# === EZ_LAST_CONFIRM_V1 ===
_EZ_LAST_CONFIRM = None
_EZ_LAST_CONFIRM_TIME = None
# === /EZ_LAST_CONFIRM_V1 ===

# === EZ_API_ROUTES_V1 ===
from pathlib import Path as _EZPath

def _ez_json_read_v1(handler):
    try:
        n = int(handler.headers.get("Content-Length","0") or "0")
    except Exception:
        n = 0
    raw = handler.rfile.read(n) if n > 0 else b""
    try:
        return json.loads(raw.decode("utf-8") or "{}")
    except Exception:
        return {}

def _ez_json_write_v1(handler, obj, code=200):
    data = json.dumps(obj).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)

def _ez_state_path_v1(handler):
    # try server attribute first (if app already uses it), else default
    sp = getattr(handler.server, "state_path", None)
    if not sp:
        sp = "/data/data/com.termux/files/home/v70_app_data/state.json"
    return sp

def _ez_load_state_v1(state_path):
    try:
        txt = _EZPath(state_path).read_text(encoding="utf-8")
        return json.loads(txt or "{}")
    except Exception:
        return {}

def _ez_save_state_v1(state):
    _EZPath(state_path).parent.mkdir(parents=True, exist_ok=True)
    _EZPath(state_path).write_text(json.dumps(state, indent=2), encoding="utf-8")

def _ez_get_balances_v1(state):
    b = state.get("balances") or {}
    cash = b.get("cash_usd", None)
    btc  = b.get("btc", None)
    try: cash = float(cash) if cash is not None else 0.0
    except Exception: cash = 0.0
    try: btc = float(btc) if btc is not None else 0.0
    except Exception: btc = 0.0
    return {"cash_usd": cash, "btc": btc}

def _ez_set_balances_v1(state, cash=None, btc=None):
    state.setdefault("balances", {})
    if cash is not None:
        try: state["balances"]["cash_usd"] = float(cash)
        except Exception: pass
    if btc is not None:
        try: state["balances"]["btc"] = float(btc)
        except Exception: pass

def _ez_append_trade_v1(state, evt):
    # only confirmed trades get written here
    side = str(evt.get("side","")).upper().strip()
    if side not in ("BUY","SELL"):
        side = "UNKNOWN"
    usd = evt.get("usd", None)
    price = evt.get("price", None)
    try: usd = float(usd) if usd is not None else None
    except Exception: usd = None
    try: price = float(price) if price is not None else None
    except Exception: price = None

    rec = {
        "type": "TRADE",
        "side": side,
        "usd": usd,
        "price": price,
        "ts": int(time.time()),
    }
    state.setdefault("history", [])
    state["history"].append(rec)
    return rec

def _ez_install_routes_comment_v1():
    # marker helper so our functions stay grouped
    return True
# === /EZ_API_ROUTES_V1 ===

# === EZ_HISTORY_ROUTES_V1 ===
_EZ_STATE_PATH = Path("/data/data/com.termux/files/home/v70_app_data/state.json")

def _ez_load_state_v1(state_path=None):
    try:
        return json.loads(_EZ_STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _ez_save_state_v1(st):
    _EZ_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _EZ_STATE_PATH.write_text(json.dumps(st, indent=2), encoding="utf-8")

def _ez_json(handler, code, payload):
    data = json.dumps(payload).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)
# === /EZ_HISTORY_ROUTES_V1 ===

#!/usr/bin/env python3
import json


import time, os, time, math
from http.server import BaseHTTPRequestHandler, HTTPServer

# === EZ_RECO_SIZING_V3 ===
EZ_COST_USD_EST = 6.00          # estimated friction per trade (fees/spread/slippage)
EZ_MIN_COST_MULT = 6.0          # min trade >= costs * multiplier
EZ_MIN_TRADE_USD_FLOOR = 25.00  # absolute minimum trade
EZ_SIZE_PCT = 0.25              # sizing: 25% of available cash/value
EZ_MAX_TRADE_USD = 5000.00      # safety cap
# === /EZ_RECO_SIZING_V3 ===


# === EZ_RECO_SIZING_V2 ===
EZ_COST_USD_EST = 6.00          # estimated friction per trade (fees/spread/slippage)
EZ_MIN_COST_MULT = 6.0          # trade must be >= costs * multiplier
EZ_MIN_TRADE_USD_FLOOR = 25.00  # absolute minimum trade
EZ_SIZE_PCT = 0.25              # 25% sizing (demo-safe; adjust later)
EZ_MAX_TRADE_USD = 5000.00      # safety cap
# === /EZ_RECO_SIZING_V2 ===


# === EZ_RECO_SIZING_V1 ===
EZ_COST_USD_EST = 6.00          # estimated round-trip friction: fees+spread+slippage (USD)
EZ_MIN_COST_MULT = 6.0          # trade should be >= costs * this multiplier
EZ_MIN_TRADE_USD_FLOOR = 25.00  # absolute min USD trade
EZ_SIZE_PCT = 0.25              # default sizing (25% of available cash/value)
EZ_MAX_TRADE_USD = 5000.00      # safety cap (set None to disable)
# === /EZ_RECO_SIZING_V1 ===


HOST = "127.0.0.1"
PORT = 8080

HOME = os.path.expanduser("~")
DATA_DIR = os.path.join(HOME, "v70_app_data")
STATE_PATH = os.path.join(DATA_DIR, "state.json")
UI_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ui"))

# ----------------- utilities -----------------
def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def load_state():
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def ensure_state():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(STATE_PATH):
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            json.dump({
                "signal": {
                    "bias": "WAIT",         # BUY / SELL / WAIT
                    "reason": "waiting for conditions",
                    "signal_price": None,   # price at signal time
                    "market_now": None,     # live/now price (set by data feed later)
                    "ts": None              # epoch seconds
                },
                "balances": {
                    "cash_usd": None,
                    "holdings_units": None
                }
            }, f, indent=2)

def compute_readiness(sig_price, mkt_now, age_sec, bias):
    """
    Returns:
      readiness (0..100), state (ALIGNED/HOLDING/PAUSED), explanation,
      drift_pct (0..), signed_alignment (-1..+1)
    """
    # Missing data -> calm pause (never "checking")
    if sig_price is None or mkt_now is None:
        return 0, "PAUSED", "Nothing is wrong. We’re just waiting for enough data.", None, 0.0

    try:
        sp = float(sig_price)
        mp = float(mkt_now)
        if sp <= 0 or mp <= 0:
            raise ValueError("bad price")
    except Exception:
        return 0, "PAUSED", "Prices are unavailable right now.", None, 0.0

    drift_pct = abs(mp - sp) / sp

    # Alignment score (primary)
    # <=0.25% strong, <=0.75% caution, >0.75% weak
    if drift_pct <= 0.0025:
        align = 1.00
    elif drift_pct <= 0.0075:
        align = 0.62
    else:
        align = 0.25

    # Time decay (soft)
    # <15m no penalty, <60m mild, >60m stronger
    if age_sec is None:
        t = 1.0
    elif age_sec < 900:
        t = 1.0
    elif age_sec < 3600:
        t = 0.75
    else:
        t = 0.55

    readiness = int(round(100 * align * t))
    readiness = clamp(readiness, 0, 100)

    # State mapping (no "checking")
    if readiness >= 70:
        state = "ALIGNED"
        expl = "Conditions are aligned."
    elif readiness >= 36:
        state = "HOLDING"
        expl = "Conditions are mixed. Patience favored."
    else:
        state = "PAUSED"
        expl = "Conditions moved away from the signal."

    # Signed alignment for the gauge direction
    # BUY leans positive, SELL leans negative, WAIT is 0
    b = (bias or "WAIT").upper()
    if b == "BUY":
        signed_alignment = +1.0
    elif b == "SELL":
        signed_alignment = -1.0
    else:
        signed_alignment = 0.0

    return readiness, state, expl, drift_pct, signed_alignment

# ----------------- http -----------------

# ============================
# EZTRADE_SERVER_ROUTES_V2
# Adds:
#   GET/POST /balances
#   GET/POST /history
#   GET/POST /records (alias of /history)
# Stores in state.json:
#   balances: {cash_usd, btc}
#   history: [events...]
# ============================

def _ez_state_path_default():
    # Keep consistent with /health output style used elsewhere
    return Path("/data/data/com.termux/files/home/v70_app_data/state.json")

def _ez_load_state_v1(state_path=None):
    p = _ez_state_path_default()
    try:
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {
        "profile": {"initialized": True},
        "balances": {"cash_usd": 10000.0, "btc": 0.25},
        "history": [],
        "meta": {"demo": True},
    }

def _ez_save_state_v1(st):
    p = _ez_state_path_default()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(st, indent=2), encoding="utf-8")

def _ez_json(handler, code, obj):
    body = json.dumps(obj).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)

def _ez_read_json(handler):
    try:
        n = int(handler.headers.get("Content-Length", "0") or "0")
    except Exception:
        n = 0
    raw = handler.rfile.read(n) if n > 0 else b"{}"
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return {}

def _ez_handle_get_balances(handler):
    st = _ez_load_state_v1()
    bal = st.get("balances") or {}
    cash = float(bal.get("cash_usd", 0.0) or 0.0)
    btc  = float(bal.get("btc", 0.0) or 0.0)
    _ez_json(handler, 200, {
        "ok": True,
        "recommended_usd": recommended_usd,
        "recommended_btc": recommended_btc,
        "pending_trade": pending_trade,
        "balances": {
            "cash_usd": cash,
            "btc": btc,
        }
    })

def _ez_handle_post_balances(handler):
    st = _ez_load_state_v1()
    bal = st.setdefault("balances", {})
    data = _ez_read_json(handler)
    if "cash_usd" in data:
        try: bal["cash_usd"] = float(data["cash_usd"])
        except Exception: pass
    if "btc" in data:
        try: bal["btc"] = float(data["btc"])
        except Exception: pass
    _ez_save_state_v1(st)
    _ez_json(handler, 200, {"ok": True, "balances": bal})

def _ez_handle_get_history(handler):
    st = _ez_load_state_v1()
    h = st.get("history") or []
    # Always return list
    if not isinstance(h, list):
        h = []
    _ez_json(handler, 200, {"ok": True, "history": h})

def _ez_handle_post_history(handler):
    st = _ez_load_state_v1()
    h = st.setdefault("history", [])
    if not isinstance(h, list):
        st["history"] = []
        h = st["history"]
    evt = _ez_read_json(handler) or {}
    # Normalize minimal fields
    evt.setdefault("ts", int(time.time()))
    evt.setdefault("type", "TRADE")
    h.append(evt)
    _ez_save_state_v1(st)
    _ez_json(handler, 200, {"ok": True, "count": len(h)})

# ============================
# /EZTRADE_SERVER_ROUTES_V2
# ============================


# === EZ_STATIC_UI_V1 ===
def _ez_serve_ui(handler, path):
    from pathlib import Path
    import mimetypes
    ui = Path("ui")
    f = (ui / path.lstrip("/")).resolve()
    if not f.exists() or ui not in f.parents:
        return False
    ctype = mimetypes.guess_type(str(f))[0] or "text/plain"
    data = f.read_bytes()
    handler.send_response(200)
    handler.send_header("Content-Type", ctype)
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)
    return True
# === /EZ_STATIC_UI_V1 ===


class Handler(BaseHTTPRequestHandler):

    def do_POST(self):
        try:
            path = self.path.split("?",1)[0]
        except Exception:
            path = self.path

        if path == "/confirm":
            evt = _ez_json_read(self)
            # === EZ_CONFIRM_NORMALIZE_V1 ===
            try:
                # UI sometimes sends 'action' instead of 'side'
                if 'side' not in evt and isinstance(evt.get('action'), str):
                    evt['side'] = evt.get('action')
                # Parse amount from note like: 'amount=310'
                if ('usd' not in evt or not evt.get('usd')) and isinstance(evt.get('note'), str):
                    m = __import__('re').search(r'amount\s*=\s*([0-9]+(?:\.[0-9]+)?)', evt['note'])
                    if m:
                        evt['usd'] = float(m.group(1))
            except Exception:
                pass
            # === /EZ_CONFIRM_NORMALIZE_V1 ===
            sp = getattr(self.server, "state_path", "/data/data/com.termux/files/home/v70_app_data/state.json")
            state = _ez_load_state(sp)

            # === EZ_CONFIRM_USE_PENDING_TRADE_V1 ===
            pending = (state or {}).get("pending_trade") or None
            try:
                side = (evt.get("side") or "").strip().upper() if isinstance(evt.get("side"), str) else ""
                usd  = float(evt.get("usd") or 0.0) if isinstance(evt.get("usd"), (int,float)) else 0.0
                prc  = float(evt.get("price") or 0.0) if isinstance(evt.get("price"), (int,float)) else 0.0
            except Exception:
                side, usd, prc = "", 0.0, 0.0

            if (not side or usd <= 0 or prc <= 0) and isinstance(pending, dict):
                try:
                    pside = (pending.get("side") or "").strip().upper()
                    pusd  = float(pending.get("usd") or 0.0)
                    pprc  = float(pending.get("price") or 0.0)
                    if pside and pusd > 0 and pprc > 0:
                        evt["side"] = pside
                        evt["usd"] = pusd
                        evt["price"] = pprc
                        side, usd, prc = pside, pusd, pprc
                except Exception:
                    pass

            if not side or usd <= 0 or prc <= 0:
                return _ez_json_write(self, {"ok": True, "trade": rec, "balances": state.get("balances", {})})
        # === EZ_API_ROUTES_V1 POST ROUTES ===
        try:
            _p = self.path.split("?",1)[0]
        except Exception:
            _p = self.path


        if _p == "/confirm":
            # === EZ_CONFIRM_APPLY_PENDING_V2 ===
            try:
                # Read request body (optional / backward compatible)
                try:
                    evt = _ez_json_read_v1(self)
                except Exception:
                    try:
                        evt = _ez_json_read(self)
                    except Exception:
                        evt = {}

                # Get state path
                try:
                    sp = _ez_state_path_v1(self)
                except Exception:
                    sp = getattr(self.server, "state_path", None) or "/data/data/com.termux/files/home/v70_app_data/state.json"

                # Load state (handle both signatures)
                try:
                    st = _ez_load_state_v1(sp)
                except TypeError:
                    st = _ez_load_state_v1()
                except Exception:
                    try:
                        st = _ez_load_state(sp)
                    except Exception:
                        st = {}

                st.setdefault("balances", {})
                bal = st["balances"]
                cash = float(bal.get("cash_usd") or 0.0)
                btc  = float(bal.get("btc") or 0.0)

                # Prefer server-side pending_trade created by /signal
                trade = st.get("pending_trade") or None

                # Fallback: if caller explicitly sends a trade
                if not isinstance(trade, dict):
                    trade = evt.get("pending_trade") if isinstance(evt, dict) else None
                if not isinstance(trade, dict):
                    trade = evt if isinstance(evt, dict) else None

                side = str((trade or {}).get("side") or "").upper()
                usd  = (trade or {}).get("usd", None)
                price = (trade or {}).get("price", None)
                try:
                    usd = float(usd) if usd is not None else None
                except Exception:
                    usd = None
                try:
                    price = float(price) if price is not None else None
                except Exception:
                    price = None

                if side not in ("BUY","SELL") or usd is None or usd <= 0 or price is None or price <= 0:
                    return _ez_json_write(self, {"ok": False, "error": "no_pending_trade"}, 400)

                # Apply balances
                if side == "BUY":
                    if cash < usd:
                        return _ez_json_write(self, {"ok": False, "error": "insufficient_cash", "balances": {"cash_usd": cash, "btc": btc}}, 400)
                    cash -= usd
                    btc += (usd / price)
                else:  # SELL
                    btc_needed = usd / price
                    if btc < btc_needed:
                        return _ez_json_write(self, {"ok": False, "error": "insufficient_btc", "balances": {"cash_usd": cash, "btc": btc}}, 400)
                    btc -= btc_needed
                    cash += usd

                # Store + clear pending
                bal["cash_usd"] = round(float(cash), 2)
                bal["btc"] = float(btc)
                applied = {"type":"TRADE","side":side,"usd":round(float(usd),2),"price":float(price),"ts":int(time.time())}
                st["last_confirm"] = applied
                st["pending_trade"] = None

                # Update globals used by /last_confirm if present
                try:
                    global _EZ_LAST_CONFIRM, _EZ_LAST_CONFIRM_TIME
                    _EZ_LAST_CONFIRM = applied
                    _EZ_LAST_CONFIRM_TIME = int(time.time())
                except Exception:
                    pass

                # Save state (handle both signatures)
                try:
                    _ez_save_state_v1(sp, st)
                except TypeError:
                    _ez_save_state_v1(st)
                except Exception:
                    try:
                        _ez_save_state(sp, st)
                    except Exception:
                        pass

                return _ez_json_write(self, {"ok": True, "applied": applied, "balances": bal}, 200)
            except Exception as e:
                return _ez_json_write(self, {"ok": False, "error": str(e)}, 500)
            # === /EZ_CONFIRM_APPLY_PENDING_V2 ===


        if _p == "/confirm":
            evt = _ez_json_read_v1(self)
            sp = _ez_state_path_v1(self)
            st = _ez_load_state_v1(sp)
            rec = _ez_append_trade_v1(st, evt)
            _ez_save_state_v1(st)
            return _ez_json_write_v1(self, {"ok": True, "logged": rec})

        if _p == "/balances":
            evt = _ez_json_read_v1(self)
            sp = _ez_state_path_v1(self)
            st = _ez_load_state_v1(sp)
            # accept cash_usd and btc keys
            cash = evt.get("cash_usd", None)
            btc  = evt.get("btc", None)
            _ez_set_balances_v1(st, cash=cash, btc=btc)
            _ez_save_state_v1(st)
            return _ez_json_write_v1(self, {"ok": True, "balances": _ez_get_balances_v1(st)})
        # === /EZ_API_ROUTES_V1 POST ROUTES ===

        # === EZ_CONFIRM_TRADE_V1 POST ROUTES ===
        try:
            path = self.path.split("?",1)[0]
        except Exception:
            path = self.path

        if path == "/confirm":
            evt = _ez_json_read(self)
            # Locate server state path if present; fallback to v70_app_data/state.json
            state_path = getattr(self.server, "state_path", None)
            if not state_path:
                state_path = "/data/data/com.termux/files/home/v70_app_data/state.json"
            state = _ez_load_state_v1(state_path)
            rec = _ez_append_trade(state, evt)
            _ez_save_state_v1(state)
            return _ez_json_write(self, {"ok": True, "logged": rec})

        return _ez_json_write(self, {"ok": False, "error": "unsupported POST"}, 404)
    def log_message(self, *args):
        return

    def send_json(self, code, obj):
        data = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def serve_html(self, path):
        if not os.path.isfile(path):
            self.send_json(404, {"ok": False})
            return
        with open(path, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):

        # === EZ_FORCE_STATIC_BAL_V1 ===
        # Absolute first: force-serve bal.html & index.html as static files
        try:
            from pathlib import Path as _P
            import mimetypes

            _path = (self.path or "/").split("?",1)[0]
            if _path in ("/", "/index.html", "/bal.html"):
                if _path == "/":
                    _path = "/index.html"

                _ui = (_P("ui") / _path.lstrip("/")).resolve()
                _root = _P("ui").resolve()

                if str(_ui).startswith(str(_root)) and _ui.exists():
                    data = _ui.read_bytes()
                    ctype, _ = mimetypes.guess_type(str(_ui))
                    if not ctype:
                        ctype = "text/html"

                    self.send_response(200)
                    self.send_header("Content-Type", ctype)
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
        except Exception:
            pass
        # === /EZ_FORCE_STATIC_BAL_V1 ===
        if self.path.endswith(".html"):
            if _ez_serve_ui(self, self.path):
                return

        # === EZ_LAST_CONFIRM_V1 GET ===
        try:
            _p = self.path.split('?',1)[0]
        except Exception:
            _p = self.path
        if _p == '/last_confirm':
            global _EZ_LAST_CONFIRM, _EZ_LAST_CONFIRM_TIME
            return _ez_json_write(self, {
                'ok': True,
                'ts': _EZ_LAST_CONFIRM_TIME,
                'evt': _EZ_LAST_CONFIRM
            })
        # === /EZ_LAST_CONFIRM_V1 GET ===

        # === EZ_API_ROUTES_V1 GET ROUTES ===
        try:
            _p = self.path.split("?",1)[0]
        except Exception:
            _p = self.path

        if _p == "/history":
            sp = _ez_state_path_v1(self)
            st = _ez_load_state_v1(sp)
            return _ez_json_write_v1(self, {"ok": True, "history": st.get("history", [])})

        if _p == "/balances":
            sp = _ez_state_path_v1(self)
            st = _ez_load_state_v1(sp)
            return _ez_json_write_v1(self, {"ok": True, "balances": _ez_get_balances_v1(st)})
        # === /EZ_API_ROUTES_V1 GET ROUTES ===

        path = _EZU.urlparse(self.path).path

        if path == "/" or path == "":
            return self.serve_html(os.path.join(UI_DIR, "index.html"))

        if path == "/health":
            return self.send_json(200, {"ok": True, "state_path": STATE_PATH, "server_time": int(time.time())})
        # === EZ_MARKET_ENDPOINT_V1 ===
        if path == "/market":
            try:
                st = load_state()
                sig = (st.get("signal") or {})
                # Prefer market_now, then signal_price
                price = sig.get("market_now", None)
                if price is None:
                    price = sig.get("signal_price", None)
                try:
                    price = float(price) if price is not None else None
                except Exception:
                    price = None
                return self.send_json(200, {"ok": True, "price": price, "server_time": int(time.time())})
            except Exception:
                return self.send_json(200, {"ok": True, "price": None, "server_time": int(time.time())})
        # === /EZ_MARKET_ENDPOINT_V1 ===

        if path == "/signal":
            st = load_state()



            # === EZ_SIGNAL_RECO_V4 ===
            recommended_usd = None
            recommended_btc = None
            pending_trade = None
            try:
                sig = st.get("signal") or {}
                bias = (sig.get("bias") or "WAIT").upper()

                mp = sig.get("market_now")
                if mp is None:
                    mp = sig.get("signal_price")
                price = float(mp) if mp is not None else None

                # Prefer unified state file used by /confirm if present
                try:
                    sp_u = getattr(self.server, "state_path", "/data/data/com.termux/files/home/v70_app_data/state.json")
                    st_u = _ez_load_state(sp_u) if "_ez_load_state" in globals() else _ez_load_state_v1(sp_u)
                    bal = (st_u.get("balances") or {})
                except Exception:
                    bal = st.get("balances") or {}

                cash_now = float(bal.get("cash_usd") or 0.0)
                btc_now  = float(bal.get("btc") or 0.0)

                # Sizing rules (simple + safe defaults)
                COST_USD_EST = float(globals().get("EZ_COST_USD_EST", 6.00))
                MIN_COST_MULT = float(globals().get("EZ_MIN_COST_MULT", 6.0))
                MIN_FLOOR = float(globals().get("EZ_MIN_TRADE_USD_FLOOR", 25.00))
                SIZE_PCT = float(globals().get("EZ_SIZE_PCT", 0.25))
                MAX_TRADE = globals().get("EZ_MAX_TRADE_USD", 5000.00)
                try:
                    MAX_TRADE = float(MAX_TRADE) if MAX_TRADE is not None else None
                except Exception:
                    MAX_TRADE = 5000.00

                min_trade = max(MIN_FLOOR, COST_USD_EST * MIN_COST_MULT)

                if price and price > 0 and bias in ("BUY","SELL"):
                    if bias == "BUY":
                        usd = max(min_trade, cash_now * SIZE_PCT)
                        usd = min(usd, cash_now)
                    else:
                        pos_value = btc_now * price
                        usd = max(min_trade, pos_value * SIZE_PCT)
                        usd = min(usd, pos_value)

                    if MAX_TRADE:
                        usd = min(usd, MAX_TRADE)

                    usd = round(float(usd), 2)
                    if usd >= min_trade and usd > 0:
                        recommended_usd = usd
                        recommended_btc = round(float(usd) / float(price), 8)
                        recommended_btc = round(float(usd) / float(price), 8)
                        pending_trade = {
                            "type": "TRADE",
                            "side": bias,
                            "usd": recommended_usd,
                            "price": float(price),
                            "ts": int(time.time()),
                        }

                        # Persist pending_trade so /confirm uses the same rec
                        try:
                            sp_u = getattr(self.server, "state_path", "/data/data/com.termux/files/home/v70_app_data/state.json")
                            st_u = _ez_load_state(sp_u) if "_ez_load_state" in globals() else _ez_load_state_v1(sp_u)
                            st_u["pending_trade"] = pending_trade
                            if "_ez_save_state" in globals():
                                _ez_save_state(sp_u, st_u)
                            else:
                                _ez_save_state_v1(sp_u, st_u)
                        except Exception:
                            pass
            except Exception:
                pass
            # === /EZ_SIGNAL_RECO_V4 ===
            # === EZ_SIGNAL_DEMOQUERY_V2 (STICKY DEMO MODE) ===
            # - If request includes demo_bias+demo_price: persist demo_mode in state file used by /confirm
            # - If request has no demo params: apply persisted demo_mode if enabled
            try:
                q = _EZU.parse_qs(_EZU.urlparse(self.path).query or "")
                demo_bias = (q.get("demo_bias", [None])[0] or "").strip().lower()
                demo_price_raw = q.get("demo_price", [None])[0]

                # Load unified state file (same one /confirm reads)
                sp_u = getattr(self.server, "state_path", "/data/data/com.termux/files/home/v70_app_data/state.json")
                st_u = _ez_load_state(sp_u)

                def _set_demo(enabled, bias=None, price=None):
                    st_u["demo_mode"] = {
                        "enabled": bool(enabled),
                        "bias": (bias or "WAIT").upper(),
                        "price": float(price) if price is not None else None,
                        "ts": int(time.time()),
                    }
                    _ez_save_state(sp_u, st_u)

                # If user explicitly changed demo mode via query, persist it
                if demo_bias in ("auto", "off", "live", "clear"):
                    _set_demo(False, "WAIT", None)
                elif demo_bias in ("buy", "sell", "wait", "notrade") and demo_price_raw is not None:
                    try:
                        dp = float(demo_price_raw)
                    except Exception:
                        dp = None
                    if dp is not None:
                        b = "WAIT" if demo_bias in ("wait", "notrade") else demo_bias.upper()
                        _set_demo(True, b, dp)

                # Apply persisted demo_mode if enabled (sticky)
                dm = (st_u.get("demo_mode") or {})
                if dm.get("enabled") and dm.get("price") is not None:
                    sig = st.get("signal") or {}
                    sig["bias"] = str(dm.get("bias") or "WAIT").upper()
                    sig["market_now"] = float(dm["price"])
                    sig["signal_price"] = float(dm["price"])
                    sig["ts"] = int(time.time())
                    sig["reason"] = "demo_mode"
                    st["signal"] = sig
            except Exception:
                pass
            # === /EZ_SIGNAL_DEMOQUERY_V2 ===
            sig = st.get("signal") or {}
            bal = st.get("balances") or {}

            bias = (sig.get("bias") or "WAIT").upper()
            reason = sig.get("reason") or ""

            sig_price = sig.get("signal_price")
            mkt_now = sig.get("market_now")
            ts = sig.get("ts")

            age_sec = None
            if isinstance(ts, (int, float)) and ts:
                age_sec = int(max(0, time.time() - float(ts)))

            readiness, state_word, expl, drift_pct, signed_dir = compute_readiness(sig_price, mkt_now, age_sec, bias)

            # Timing impact per unit: BUY => mp-sp, SELL => sp-mp
            timing_per_unit = None
            if sig_price is not None and mkt_now is not None:
                try:
                    sp = float(sig_price); mp = float(mkt_now)
                    if bias == "BUY": timing_per_unit = round(mp - sp, 2)
                    elif bias == "SELL": timing_per_unit = round(sp - mp, 2)
                    else: timing_per_unit = round(mp - sp, 2)
                except Exception:
                    timing_per_unit = None

            # Suggested size (placeholder conservative) if cash is known
            timing_suggested = None
            cash = bal.get("cash_usd")
            if timing_per_unit is not None and isinstance(cash, (int, float)):
                # conservative: 25% of cash, min $10
                usd = max(10.0, float(cash) * 0.25)
                # estimate units
                try:
                    units = usd / float(mkt_now) if mkt_now else 0.0
                    timing_suggested = round(timing_per_unit * units, 2)
                except Exception:
                    timing_suggested = None
            # === EZ_PENDING_TRADE_V2 (unified state file used by /confirm) ===
            try:
                pending = None
                if bias in ("BUY", "SELL") and mkt_now is not None:
                    price = float(mkt_now)
                    cash_now = float((bal or {}).get("cash_usd") or 0.0)
                    btc_now  = float((bal or {}).get("btc") or 0.0)

                    if bias == "BUY":
                        usd_suggest = max(10.0, cash_now * 0.25)
                        usd_suggest = min(usd_suggest, cash_now)
                    else:
                        holdings_value = btc_now * price
                        usd_suggest = max(10.0, holdings_value * 0.25)
                        usd_suggest = min(usd_suggest, holdings_value)

                    pending = {
                        "type": "TRADE",
                        "side": bias,
                        "usd": round(float(usd_suggest), 2),
                        "price": float(price),
                        "ts": int(time.time()),
                    }

                # IMPORTANT: write pending_trade to the same state file /confirm uses
                sp = getattr(self.server, "state_path", "/data/data/com.termux/files/home/v70_app_data/state.json")
                st2 = _ez_load_state(sp)
                if (st2.get("pending_trade") or None) != pending:
                    st2["pending_trade"] = pending
                    _ez_save_state(sp, st2)
            except Exception:
                pass
            # === /EZ_PENDING_TRADE_V2 ===

            # === EZ_SIGNAL_PENDING_EXPORT_V1 ===
            pending_trade = None
            recommended_usd = None
            try:
                sp_u = getattr(self.server, "state_path", "/data/data/com.termux/files/home/v70_app_data/state.json")
                st_u = _ez_load_state(sp_u)
                pending_trade = (st_u.get("pending_trade") or None)
                if isinstance(pending_trade, dict):
                    try:
                        recommended_usd = float(pending_trade.get("usd") or 0.0)
                        if recommended_usd <= 0: recommended_usd = None
                    except Exception:
                        recommended_usd = None
            except Exception:
                pending_trade = None
                recommended_usd = None
            # === /EZ_SIGNAL_PENDING_EXPORT_V1 ===
            return self.send_json(200, {
                "ok": True,
                "recommended_usd": recommended_usd,
                "recommended_btc": recommended_btc,
                "pending_trade": pending_trade,
                "bias": bias,                 # BUY / SELL / WAIT
                "state": state_word,          # ALIGNED / HOLDING / PAUSED
                "readiness": readiness,       # 0..100
                "explanation": expl,
                "reason": reason,
                "signal_price": sig_price,
                "market_now": mkt_now,
                "age_sec": age_sec,
                "drift_pct": drift_pct,
                "timing_per_unit": timing_per_unit,
                "timing_suggested": timing_suggested,
                "server_time": int(time.time())
            })


        return self.send_json(404, {"ok": False})

def main():
    ensure_state()
    httpd = HTTPServer((HOST, PORT), Handler)
    print(f"EZTrade server v2 running on http://{HOST}:{PORT}")
    httpd.serve_forever()

if __name__ == "__main__":
    main()


# === EZ_LOADSTATE_COMPAT_V1 ===
# Fix signature conflict: older code defines _ez_load_state_v1() with 0 args.
# Newer confirm routes call _ez_load_state_v1(state_path).
# This wrapper supports BOTH safely.

try:
    _ez__old_load_state = _ez_load_state  # may be 0-arg
except Exception:
    _ez__old_load_state = None

def _ez_load_state_v1(state_path=None):
    # If called with no args and an old loader exists, use it.
    if state_path is None and callable(_ez__old_load_state):
        try:
            return _ez__old_load_state()
        except Exception:
            pass

    # If called with a path, load JSON from that path.
    try:
        import json


        from pathlib import Path
        txt = Path(state_path).read_text(encoding="utf-8")
        return json.loads(txt or "{}")
    except Exception:
        return {}

def _ez_save_state_v1(state):
    try:
        import json


        from pathlib import Path
        Path(state_path).parent.mkdir(parents=True, exist_ok=True)
        Path(state_path).write_text(json.dumps(state, indent=2), encoding="utf-8")
        return True
    except Exception:
        return False

# Also provide a simple GET /history handler if not already present.
# We patch do_GET in-place by wrapping it (safe even if do_GET already exists).
try:
    _ez__orig_do_GET = globals().get("_ez__orig_do_GET", None)
except Exception:
    _ez__orig_do_GET = None
# === /EZ_LOADSTATE_COMPAT_V1 ===
