#!/usr/bin/env python3
import json, os, time
import re
from app.paths import ENGINE_STATE_PATH, APP_STATE_PATH, CONFIRM_PATH, SETTINGS_PATH, ALERTS_PATH, ensure_dirs


# EZ_ALERTS_POST_PERSIST_V1
def _ez_alerts_json_path():
    """Store alerts at canonical ALERTS_PATH (v71+)."""
    return ALERTS_PATH
def _ez_load_alerts():
    import json, os
    p = _ez_alerts_json_path()
    dflt = {
        "enabled": True,
        "notify": True,
        "vibrate": True,
        "speak": True,
        "poll_sec": 10,
        "repeat_sec": 0,
        "quiet": {
            "enabled": False,
            "start": "22:00",
            "end": "07:00",
            "allow": {"notify": False, "vibrate": False, "speak": False}
        }
    }
    try:
        if os.path.exists(p):
            data = json.load(open(p, "r", encoding="utf-8"))
            if isinstance(data, dict):
                # merge shallow + quiet
                out = dict(dflt)
                out.update(data)
                if isinstance(data.get("quiet"), dict):
                    q = dict(dflt["quiet"])
                    q.update(data["quiet"])
                    if isinstance(data["quiet"].get("allow"), dict):
                        a = dict(dflt["quiet"]["allow"])
                        a.update(data["quiet"]["allow"])
                        q["allow"] = a
                    out["quiet"] = q
                return out, p
    except Exception:
        pass
    return dflt, p

def _ez_save_alerts(payload):
    import json, os, time
    cur, p = _ez_load_alerts()
    if not isinstance(payload, dict):
        return cur, p
    # allow only known keys
    for k in ("enabled","notify","vibrate","speak"):
        if k in payload:
            cur[k] = bool(payload[k])
    if "poll_sec" in payload:
        try: cur["poll_sec"] = max(2, int(payload["poll_sec"]))
        except Exception: pass
    if "repeat_sec" in payload:
        try: cur["repeat_sec"] = max(0, int(payload["repeat_sec"]))
        except Exception: pass
    if isinstance(payload.get("quiet"), dict):
        q = cur.get("quiet") if isinstance(cur.get("quiet"), dict) else {}
        for k in ("enabled","start","end"):
            if k in payload["quiet"]:
                q[k] = payload["quiet"][k]
        if isinstance(payload["quiet"].get("allow"), dict):
            a = q.get("allow") if isinstance(q.get("allow"), dict) else {}
            for k in ("notify","vibrate","speak"):
                if k in payload["quiet"]["allow"]:
                    a[k] = bool(payload["quiet"]["allow"][k])
            q["allow"] = a
        cur["quiet"] = q
    cur["updated_at"] = time.strftime("%Y-%m-%d %I:%M:%S %p")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(cur, open(p, "w", encoding="utf-8"), indent=2)
    return cur, p

# --- Live price helper (Kraken, no key) ---
def _ez_live_kraken_btc_usd(timeout_sec: float = 2.5):
    """
    Returns float live BTC-USD from Kraken, or None.
    Kraken pair is XBTUSD.
    """
    try:
        import urllib.request, json
        url = "https://api.kraken.com/0/public/Ticker?pair=XBTUSD"
        with urllib.request.urlopen(url, timeout=timeout_sec) as r:
            j = json.loads(r.read().decode("utf-8"))
        res = (j.get("result") or {})
        if not isinstance(res, dict) or not res:
            return None
        # result key may vary; take first
        k = next(iter(res.keys()))
        c = (res.get(k) or {}).get("c")  # last trade closed [price, lot]
        if not c or not isinstance(c, (list, tuple)) or not c[0]:
            return None
        px = float(c[0])
        return px if px > 0 else None
    except Exception:
        return None
# --- end helper ---



# --- Kraken OHLC helper (no key) ---

# EZ_SYMBOL_ROUTING_V2 (crypto-only)
_KRAKEN_PAIR = {
    "BTC-USD": "XBTUSD",
    "ETH-USD": "ETHUSD",
    "SOL-USD": "SOLUSD",
    "DOGE-USD": "DOGEUSD",
    "XRP-USD": "XRPUSD",
}

def _ez_norm_symbol(sym):
    try:
        sym = (sym or "").strip().upper()
    except Exception:
        sym = "BTC-USD"
    if sym in ("BTCUSD", "XBTUSD", "XBT-USD"): return "BTC-USD"
    if sym in ("ETHUSD", "ETH-USD"): return "ETH-USD"
    if sym in ("SOLUSD", "SOL-USD"): return "SOL-USD"
    if sym in ("DOGEUSD","DOGE-USD"): return "DOGE-USD"
    if sym in ("XRPUSD", "XRP-USD"): return "XRP-USD"
    if sym in _KRAKEN_PAIR: return sym
    return "BTC-USD"

def _ez_kraken_pair(sym):
    sym = _ez_norm_symbol(sym)
    return _KRAKEN_PAIR.get(sym)

def _ez_live_kraken_price_symbol(symbol, timeout_sec=2.5):
    pair = _ez_kraken_pair(symbol)
    if not pair:
        return None
    try:
        import urllib.request, json
        url = "https://api.kraken.com/0/public/Ticker?pair=" + pair
        raw = urllib.request.urlopen(url, timeout=timeout_sec).read().decode("utf-8", "replace")
        j = json.loads(raw) if raw else {}
        res = (j or {}).get("result") or {}
        if isinstance(res, dict) and res:
            v = next(iter(res.values()))
            c = v.get("c") if isinstance(v, dict) else None
            return float(c[0]) if (isinstance(c, list) and c and c[0] is not None) else None
    except Exception:
        return None
    return None

def _ez_kraken_ohlc_symbol(symbol, interval_min=5, since=None, timeout_sec=6.0):
    pair = _ez_kraken_pair(symbol)
    if not pair:
        return []
    try:
        import urllib.request, json
        url = f"https://api.kraken.com/0/public/OHLC?pair={pair}&interval={int(interval_min)}"
        if since is not None:
            url += f"&since={int(since)}"
        raw = urllib.request.urlopen(url, timeout=timeout_sec).read().decode("utf-8", "replace")
        j = json.loads(raw) if raw else {}
        res = (j or {}).get("result") or {}
        if not isinstance(res, dict) or not res:
            return []
        ohlc = None
        for k, v in res.items():
            if k == "last":
                continue
            if isinstance(v, list):
                ohlc = v
                break
        if not ohlc:
            return []
        out = []
        for row in ohlc:
            try:
                out.append({
                    "time": int(row[0]),
                    "open": float(row[1]),
                    "high": float(row[2]),
                    "low": float(row[3]),
                    "close": float(row[4]),
                })
            except Exception:
                continue
        return out
    except Exception:
        return []

def _ez_kraken_ohlc(interval_min: int = 5, since: int | None = None, timeout_sec: float = 6.0):
    """Return list of candlesticks for Lightweight Charts: [{time, open, high, low, close}, ...]."""
    try:
        import urllib.request, json
        interval_min = int(interval_min or 5)
        if interval_min not in (1, 5, 15, 30, 60, 240, 1440, 10080, 21600):
            interval_min = 5
        url = f"https://api.kraken.com/0/public/OHLC?pair=XBTUSD&interval={interval_min}"
        if since is not None:
            try:
                since = int(since)
                if since > 0:
                    url += f"&since={since}"
            except Exception:
                pass
        with urllib.request.urlopen(url, timeout=timeout_sec) as r:
            j = json.loads(r.read().decode("utf-8"))
        res = (j.get("result") or {})
        pair_key = None
        for k in res.keys():
            if k != "last":
                pair_key = k
                break
        rows = res.get(pair_key) if pair_key else None
        out = []
        if isinstance(rows, list):
            for row in rows:
                try:
                    t = int(row[0])
                    o = float(row[1]); h = float(row[2]); l = float(row[3]); c = float(row[4])
                    out.append({"time": t, "open": o, "high": h, "low": l, "close": c})
                except Exception:
                    continue
        return out
    except Exception:
        return []
# --- end OHLC helper ---
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs



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

# =========================
# Portfolio (v70+) helpers
# =========================

DEFAULT_PORTFOLIO_SYMBOLS = [
    "BTC-USD","ETH-USD","SOL-USD","XRP-USD","ADA-USD",
    "DOGE-USD","AVAX-USD","LINK-USD","MATIC-USD","LTC-USD"
]

_portfolio_cache = {"ts": 0, "data": None}

def _portfolio_defaults(settings: dict) -> dict:
    """Ensure portfolio fields exist; migrate legacy manual_btc_qty if present."""
    if not isinstance(settings, dict):
        settings = {}

    # Portfolio symbol list
    syms = settings.get("portfolio_symbols")
    if not isinstance(syms, list) or not syms:
        settings["portfolio_symbols"] = DEFAULT_PORTFOLIO_SYMBOLS[:]
    else:
        # normalize to USD pairs only
        norm = []
        for x in syms:
            if not isinstance(x, str):
                continue
            x = x.strip().upper()
            if x.endswith("-USD") and re.match(r"^[A-Z0-9]{2,12}-USD$", x):
                if x not in norm:
                    norm.append(x)
        settings["portfolio_symbols"] = norm or DEFAULT_PORTFOLIO_SYMBOLS[:]

    # Manual holdings qty map (truth = qty)
    mh = settings.get("manual_holdings_qty")
    if not isinstance(mh, dict):
        mh = {}
    # migrate legacy BTC qty if present
    if "manual_btc_qty" in settings and "BTC-USD" not in mh:
        try:
            mh["BTC-USD"] = float(settings.get("manual_btc_qty") or 0.0)
        except Exception:
            mh["BTC-USD"] = 0.0
    # ensure floats
    mh2 = {}
    for k,v in mh.items():
        if not isinstance(k, str):
            continue
        kk = k.strip().upper()
        if not (kk.endswith("-USD") and re.match(r"^[A-Z0-9]{2,12}-USD$", kk)):
            continue
        try:
            mh2[kk] = float(v)
        except Exception:
            mh2[kk] = 0.0
    settings["manual_holdings_qty"] = mh2

    # Keep legacy fields for compatibility (ok if present)
    if "manual_cash_usd" not in settings:
        settings["manual_cash_usd"] = float(settings.get("cash_usd") or 0.0)

    return settings

def _fetch_coinbase_spot(symbol: str) -> float:
    """
    Fetch Coinbase spot price. symbol must be like 'BTC-USD'.
    Returns float price or 0.0 if unavailable.
    """
    import json, urllib.request
    try:
        sym = symbol.strip().upper()
        if not (sym.endswith("-USD") and re.match(r"^[A-Z0-9]{2,12}-USD$", sym)):
            return 0.0
        url = f"https://api.coinbase.com/v2/prices/{sym}/spot"
        req = urllib.request.Request(url, headers={"User-Agent":"EZTrader/1.0"})
        with urllib.request.urlopen(req, timeout=6) as r:
            j = json.loads(r.read().decode("utf-8","replace"))
        amt = (((j or {}).get("data") or {}).get("amount")) or ""
        return float(amt)
    except Exception:
        return 0.0

def _build_portfolio_payload(settings: dict) -> dict:
    """
    Returns dict with:
      cash, holdings{symbol:qty}, prices{symbol:price}, values{symbol:usd}, total_usd
    Cached briefly to avoid hammering API.
    """
    global _portfolio_cache
    now = time.time()
    if _portfolio_cache["data"] is not None and (now - _portfolio_cache["ts"]) < 8:
        return _portfolio_cache["data"]

    st = _portfolio_defaults(dict(settings or {}))
    syms = st.get("portfolio_symbols") or []
    holdings = st.get("manual_holdings_qty") or {}
    cash = float(st.get("manual_cash_usd") or 0.0)

    prices = {}
    values = {}
    total = cash

    for sym in syms:
        qty = float(holdings.get(sym) or 0.0)
        px = _fetch_coinbase_spot(sym)
        prices[sym] = px
        usd = (qty * px) if (px and qty) else 0.0
        values[sym] = usd
        total += usd

    payload = {
        "ok": True,
        "cash_usd": cash,
        "symbols": syms,
        "holdings_qty": {k: float(holdings.get(k) or 0.0) for k in syms},
        "prices": prices,
        "values_usd": values,
        "total_usd": total,
        "source": "coinbase_spot",
        "cached_sec": 8
    }
    _portfolio_cache = {"ts": now, "data": payload}
    return payload


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


# EZ_SIGNALS_HELPER_V1
def _ez_rsi(values, period=14):
    # returns list same length as values (None where not available)
    n = len(values)
    out = [None]*n
    if n < period + 1:
        return out
    gains = [0.0]*n
    losses = [0.0]*n
    for i in range(1, n):
        d = float(values[i]) - float(values[i-1])
        gains[i] = d if d > 0 else 0.0
        losses[i] = (-d) if d < 0 else 0.0

    # initial average
    avg_gain = sum(gains[1:period+1]) / period
    avg_loss = sum(losses[1:period+1]) / period
    if avg_loss == 0:
        out[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        out[period] = 100.0 - (100.0 / (1.0 + rs))

    # Wilder smoothing
    for i in range(period+1, n):
        avg_gain = (avg_gain*(period-1) + gains[i]) / period
        avg_loss = (avg_loss*(period-1) + losses[i]) / period
        if avg_loss == 0:
            out[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            out[i] = 100.0 - (100.0 / (1.0 + rs))
    return out

def _ez_build_signals_from_candles(candles):
    # candles: list of dicts: {time, open, high, low, close}
    arr = []
    for c in (candles or []):
        try:
            t = int(c.get("time") or c.get("t") or c.get("timestamp") or c.get("ts") or 0)
        except Exception:
            t = 0
        try:
            cl = float(c.get("close") if isinstance(c, dict) else c[4])
        except Exception:
            try:
                cl = float(c.get("c"))
            except Exception:
                continue
        if t:
            arr.append({"time": t, "close": cl})

    closes = [x["close"] for x in arr]
    rsis = _ez_rsi(closes, 14)

    signals = []
    prev = None
    for i in range(len(arr)):
        r = rsis[i]
        if r is None:
            continue
        if prev is not None:
            # RSI cross rules (simple + stable)
            if prev >= 30.0 and r < 30.0:
                signals.append({"time": int(arr[i]["time"]), "side": "BUY", "price": float(arr[i]["close"]), "rsi": float(r)})
            elif prev <= 70.0 and r > 70.0:
                signals.append({"time": int(arr[i]["time"]), "side": "SELL", "price": float(arr[i]["close"]), "rsi": float(r)})
        prev = r
    return signals


HOST = os.environ.get("V70_HOST", "127.0.0.1")
PORT = int(os.environ.get("V70_PORT", "8080"))
# APP data (v70): confirmations live here

# === ALERTS (UI-exposed) ===
HOST_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ALERTS_ENV_PATH = os.environ.get("V70_ALERTS_ENV_PATH", os.path.join(HOST_DIR, "alerts.env"))

ALERTS_ALLOWED_KEYS = {
    # core
    "PRESET_NAME",
    "ALERTS_ENABLED",
    "POLL_SEC",
    "REPEAT_SEC",
    "CURL_MAX_TIME",
    "STOP_ON_CONFIRM",
    "SPEAK",
    "NOTIFY",
    "VIBRATE",
    # quiet
    "QUIET_ENABLED",
    "QUIET_START",
    "QUIET_END",
    "QUIET_ALLOW_NOTIFY",
    "QUIET_ALLOW_VIBRATE",
    "QUIET_ALLOW_SPEAK",
    # advanced (optional)
    "PRICE_MOVE_ENABLED",
    "PRICE_MOVE_THRESHOLD_PCT",
    "PRICE_MOVE_WINDOW_MIN",
    "PRICE_MOVE_DIRECTION",
    "PRICE_MOVE_OVERRIDE_QUIET",
    "WAKE_TRADE_ENABLED",
    "WAKE_TRADE_MIN_USD",
    "WAKE_TRADE_PCT_OF_CASH",
    "WAKE_TRADE_OVERRIDE_QUIET",
}

def _read_env_kv(path: str) -> dict:
    try:
        txt = _Path(path).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return {}
    out = {}
    for line in txt.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip()
        out[k] = v
    return out

def _write_env_kv(path: str, kv: dict):
    # write clean KEY=VALUE only (safe for bash source)
    lines = []
    lines.append("# ===== EZTrader Alerts User Options (UI-managed) =====")
    lines.append("# Lines must be KEY=VALUE only. Comments must be on their own line.")
    # stable-ish ordering: known keys first
    order = [
        "PRESET_NAME",
        "ALERTS_ENABLED","POLL_SEC","REPEAT_SEC","CURL_MAX_TIME","STOP_ON_CONFIRM",
        "SPEAK","NOTIFY","VIBRATE",
        "QUIET_ENABLED","QUIET_START","QUIET_END","QUIET_ALLOW_NOTIFY","QUIET_ALLOW_VIBRATE","QUIET_ALLOW_SPEAK",
        "PRICE_MOVE_ENABLED","PRICE_MOVE_THRESHOLD_PCT","PRICE_MOVE_WINDOW_MIN","PRICE_MOVE_DIRECTION","PRICE_MOVE_OVERRIDE_QUIET",
        "WAKE_TRADE_ENABLED","WAKE_TRADE_MIN_USD","WAKE_TRADE_PCT_OF_CASH","WAKE_TRADE_OVERRIDE_QUIET",
    ]
    seen = set()
    for k in order:
        if k in kv:
            v = str(kv[k]).strip()
            lines.append(f"{k}={v}")
            seen.add(k)
    # any extras (keep clean)
    for k in sorted(kv.keys()):
        if k in seen:
            continue
        v = str(kv[k]).strip()
        if not k or any(c in k for c in " \t\r\n#"):
            continue
        lines.append(f"{k}={v}")
    _Path(path).parent.mkdir(parents=True, exist_ok=True)
    _Path(path).write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

def _hhmm_to_min(hhmm: str) -> int:
    hhmm = (hhmm or "").strip()
    if not re.match(r"^\d{2}:\d{2}$", hhmm):
        return 0
    h, m = hhmm.split(":")
    return int(h)*60 + int(m)

def _quiet_active_now(cfg: dict) -> bool:
    try:
        if str(cfg.get("QUIET_ENABLED","0")).strip() != "1":
            return False
        qs = str(cfg.get("QUIET_START","22:00")).strip()
        qe = str(cfg.get("QUIET_END","07:00")).strip()
        now_hm = time.strftime("%H:%M")
        now = _hhmm_to_min(now_hm)
        s = _hhmm_to_min(qs)
        e = _hhmm_to_min(qe)
        if s <= e:
            return (now >= s) and (now < e)
        # wraps midnight
        return (now >= s) or (now < e)
    except Exception:
        return False

def _effective_now(cfg: dict) -> dict:
    # effective notify/vibrate/speak considering quiet rules
    quiet = _quiet_active_now(cfg)
    speak = 1 if str(cfg.get("SPEAK","0")).strip() == "1" else 0
    notify = 1 if str(cfg.get("NOTIFY","1")).strip() == "1" else 0
    vibrate = 1 if str(cfg.get("VIBRATE","1")).strip() == "1" else 0

    if quiet:
        if str(cfg.get("QUIET_ALLOW_SPEAK","0")).strip() != "1":
            speak = 0
        if str(cfg.get("QUIET_ALLOW_NOTIFY","0")).strip() != "1":
            notify = 0
        if str(cfg.get("QUIET_ALLOW_VIBRATE","0")).strip() != "1":
            vibrate = 0

    return {"quiet_active_now": bool(quiet), "effective": {"SPEAK": speak, "NOTIFY": notify, "VIBRATE": vibrate}}

def _validate_alerts_patch(patch: dict) -> dict:
    if not isinstance(patch, dict):
        raise ValueError("bad payload")
    out = {}
    for k, v in patch.items():
        if k not in ALERTS_ALLOWED_KEYS:
            continue
        if v is None:
            continue
        s = str(v).strip()
        # block anything that would break env file
        if any(x in s for x in ["\n","\r"]):
            raise ValueError(f"bad {k}")
        # numeric keys
        if k in {"ALERTS_ENABLED","SPEAK","NOTIFY","VIBRATE","STOP_ON_CONFIRM","QUIET_ENABLED",
                 "QUIET_ALLOW_NOTIFY","QUIET_ALLOW_VIBRATE","QUIET_ALLOW_SPEAK",
                 "PRICE_MOVE_ENABLED","PRICE_MOVE_OVERRIDE_QUIET",
                 "WAKE_TRADE_ENABLED","WAKE_TRADE_OVERRIDE_QUIET"}:
            if s not in {"0","1"}:
                raise ValueError(f"bad {k}")
            out[k] = s
            continue
        if k in {"POLL_SEC","REPEAT_SEC","CURL_MAX_TIME","PRICE_MOVE_WINDOW_MIN"}:
            try:
                n = int(float(s))
                if n < 0: raise ValueError()
            except Exception:
                raise ValueError(f"bad {k}")
            out[k] = str(n)
            continue
        if k in {"PRICE_MOVE_THRESHOLD_PCT","WAKE_TRADE_MIN_USD","WAKE_TRADE_PCT_OF_CASH"}:
            try:
                f = float(s)
                if f < 0: raise ValueError()
            except Exception:
                raise ValueError(f"bad {k}")
            # keep compact
            out[k] = str(f).rstrip("0").rstrip(".") if "." in str(f) else str(f)
            continue
        if k in {"QUIET_START","QUIET_END"}:
            if not re.match(r"^\d{2}:\d{2}$", s):
                raise ValueError(f"bad {k}")
            out[k] = s
            continue
        if k == "PRICE_MOVE_DIRECTION":
            s2 = s.lower()
            if s2 not in {"up","down","both"}:
                raise ValueError("bad PRICE_MOVE_DIRECTION")
            out[k] = s2
            continue
        # PRESET_NAME or anything else in allowed list:
        out[k] = s.replace(" ", "_")
    return out
# === END ALERTS (UI-exposed) ===



# ENGINE data (v69): signals come from here (authoritative)

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
        "pos_side", "pos_qty", "pos_entry_price",
        "manual_cash_usd", "manual_btc_usd", "manual_btc_qty",

                "poll_mode",
                "poll_signal_sec", "poll_reco_sec", "poll_intel_sec", "poll_health_sec",
                "bg_multiplier", "pause_when_hidden",
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



    # position (manual; for UI state only)
    if "pos_side" in payload:
        ps = payload.get("pos_side")
        if ps is None or ps == "":
            out["pos_side"] = "FLAT"
            changed["pos_side"] = "FLAT"
        else:
            ps = str(ps).strip().upper()
            if ps not in ("FLAT", "LONG"):
                raise ValueError("bad pos_side")
            out["pos_side"] = ps
            changed["pos_side"] = ps

    for k in ("pos_qty", "pos_entry_price"):
        if k in payload:
            v = payload.get(k)
            if v is None or v == "":
                out[k] = None
                changed[k] = None
                continue
            try:
                fv = float(v)
            except Exception:
                raise ValueError(f"bad {k}")
            if fv < 0:
                raise ValueError(f"bad {k}")
            # entry price should be > 0 if provided
            if k == "pos_entry_price" and fv == 0:
                raise ValueError("bad pos_entry_price")
            out[k] = fv
            changed[k] = fv


    # manual balances (tracking only)
    for k in ("manual_cash_usd", "manual_btc_usd", "manual_btc_qty"):
        if k in payload:
            v = payload.get(k)
            if v is None or v == "":
                out[k] = None
                changed[k] = None
                continue
            try:
                fv = float(v)
            except Exception:
                raise ValueError(f"bad {k}")
            if fv < 0:
                raise ValueError(f"bad {k}")
            out[k] = fv
            changed[k] = fv


    # manual position tracking (not connected to broker)
    if "pos_side" in payload and payload.get("pos_side") is not None:
        ps = str(payload.get("pos_side")).strip().upper()
        if ps not in ("FLAT", "LONG"):
            raise ValueError("bad pos_side")
        out["pos_side"] = ps
        changed["pos_side"] = ps

    for k in ("pos_qty", "pos_entry_price"):
        if k in payload:
            v = payload.get(k)
            if v is None or v == "":
                out[k] = None
                changed[k] = None
                continue
            try:
                fv = float(v)
            except Exception:
                raise ValueError(f"bad {k}")
            if fv < 0:
                raise ValueError(f"bad {k}")
            out[k] = fv
            changed[k] = fv


    # position state (manual, beginner-friendly)
    # pos_side: FLAT/LONG/SHORT
    if "pos_side" in payload and payload.get("pos_side") is not None:
        ps = str(payload.get("pos_side")).strip().upper()
        if ps not in ("FLAT", "LONG", "SHORT"):
            raise ValueError("bad pos_side")
        out["pos_side"] = ps
        changed["pos_side"] = ps

    # pos_qty / pos_entry_price: float or None
    for k in ("pos_qty", "pos_entry_price"):
        if k in payload:
            v = payload.get(k)
            if v is None or v == "":
                out[k] = None
                changed[k] = None
                continue
            try:
                fv = float(v)
            except Exception:
                raise ValueError(f"bad {k}")
            if fv < 0:
                raise ValueError(f"bad {k}")
            out[k] = fv
            changed[k] = fv


    # position (manual) — persisted UI state
    if "pos_side" in payload:
        v = payload.get("pos_side")
        if v is None or v == "":
            # ignore blank
            pass
        else:
            side = str(v).strip().upper()
            if side not in ("FLAT", "LONG", "SHORT"):
                raise ValueError("bad pos_side")
            out["pos_side"] = side
            changed["pos_side"] = side
            # If user sets FLAT, clear position numbers
            if side == "FLAT":
                out["pos_qty"] = None
                out["pos_entry_price"] = None
                changed["pos_qty"] = None
                changed["pos_entry_price"] = None

    for k in ("pos_qty", "pos_entry_price"):
        if k in payload:
            v = payload.get(k)
            if v is None or v == "":
                out[k] = None
                changed[k] = None
                continue
            try:
                fv = float(v)
            except Exception:
                raise ValueError(f"bad {k}")
            if k == "pos_qty":
                if fv < 0:
                    raise ValueError("bad pos_qty")
            else:
                # entry price must be >0 if provided
                if fv <= 0:
                    raise ValueError("bad pos_entry_price")
            out[k] = fv
            changed[k] = fv

    # position fields (manual tracking)
    if "pos_side" in payload:
        v = payload.get("pos_side")
        v = "FLAT" if v is None else str(v).strip().upper()
        if v not in ("FLAT", "LONG", "SHORT"):
            raise ValueError("bad pos_side")
        out["pos_side"] = v
        changed["pos_side"] = v

    for k in ("pos_qty", "pos_entry_price"):
        if k in payload:
            v = payload.get(k)
            if v is None or str(v).strip() == "":
                out[k] = None
                changed[k] = None
            else:
                try:
                    fv = float(v)
                except Exception:
                    raise ValueError(f"bad {k}")
                if fv < 0:
                    raise ValueError(f"bad {k}")
                out[k] = fv
                changed[k] = fv

    return out, changed

    # EZ_SYNC_POS_QTY_TO_MANUAL_BTC_V2
    # Enforce single source of truth:
    # position qty ALWAYS mirrors manual BTC qty
    try:
        if isinstance(s, dict):
            s["pos_qty"] = float(s.get("manual_btc_qty") or 0.0)
    except Exception:
        pass




def _load_settings():
    s = _read_json(SETTINGS_PATH)
    if not isinstance(s, dict):
        s = _default_settings()
        _write_json(SETTINGS_PATH, s)
    # default minimum trade (USD)
    if "min_trade_usd" not in s:
        s["min_trade_usd"] = 25

    # apply active intel profile from settings (startup consistency)
    global EZ_INTEL_ACTIVE_PROFILE
    try:
        ip = str((s or {}).get("intel_profile") or EZ_INTEL_ACTIVE_PROFILE or "balanced").strip().lower()
        if ip in EZ_INTEL_PROFILES:
            EZ_INTEL_ACTIVE_PROFILE = ip
    except Exception:
        pass


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

            # __EZ_AUTOSYNC_MANUAL_AFTER_CONFIRM
            # After CONFIRM, sync manual tracking balances to match engine/app_state so UI stays coherent.
            try:
                from pathlib import Path as _Path
                _home = _Path.home()
                _app_state_path = _home / "v69_app_data" / "app_state.json"
                _st = _read_json(_app_state_path) or {}

                # Determine symbol + price (best-effort)
                _symbol = "BTC-USD"
                _price = 0.0
                try:
                    # confirm dict commonly exists in this scope
                    _symbol = (confirm.get("symbol") or confirm.get("sym") or _symbol)
                    _price = float(confirm.get("price") or confirm.get("engine_price") or confirm.get("live_price") or 0.0)
                except Exception:
                    pass
                try:
                    if not _price:
                        _engine = _load_json(ENGINE_STATE_PATH)
                        if isinstance(_engine, dict):
                            _p = (_engine.get("primary") or {})
                            _symbol = (_p.get("symbol") or _engine.get("symbol") or _symbol)
                            _price = float(_p.get("price") or _engine.get("price") or 0.0)
                except Exception:
                    pass

                # Pull cash + holdings from app_state.json
                _cash = float(_st.get("cash_usd", _st.get("usd", 0.0)) or 0.0)
                _h = (_st.get("holdings") or {})
                _qty = 0.0
                try:
                    if isinstance(_h, dict):
                        _qty = float(_h.get(_symbol, _h.get("BTC-USD", _h.get("BTC", 0.0))) or 0.0)
                except Exception:
                    _qty = 0.0

                _btc_usd = (_qty * _price) if (_price and _qty) else 0.0

                # Write into v70 settings (manual tracking snapshot)
                _settings_obj = _load_settings() or {}
                if isinstance(_settings_obj, dict):
                    _settings_obj["manual_cash_usd"] = round(_cash, 2)
                    _settings_obj["manual_btc_qty"] = round(_qty, 12)
                    _settings_obj["manual_btc_usd"] = round(_btc_usd, 2)
                    _settings_obj["updated_at"] = time.strftime("%Y-%m-%d %I:%M:%S %p")
                    _write_json(SETTINGS_PATH, _settings_obj)
            except Exception:
                pass
            # --- end autosync ---

            return self._send_json(200, {
                "ok": True,
                "engine_state_path": ENGINE_STATE_PATH,
                "engine_state_readable": bool(engine is not None),
                "app_state_path": APP_STATE_PATH,
                "app_state_readable": bool(appst is not None),
                "confirm_path": CONFIRM_PATH})

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
            try:
                _ep = sig.get("price")
                _lp = _ez_live_kraken_btc_usd(timeout_sec=2.5)
                if _lp is not None:
                    sig["engine_price"] = _ep
                    sig["price"] = _lp
            except Exception:
                pass
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
                    "https://api.kraken.com/0/public/Ticker?pair=XBTUSD",
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

            # Live price for /reco (Coinbase spot, no API key). If it fails, keep engine price.
            engine_price = price
            try:
                import urllib.request as _u, json as _j
                with _u.urlopen("https://api.kraken.com/0/public/Ticker?pair=XBTUSD", timeout=EZ_INTEL_GUARDRAILS["HTTP_TIMEOUT_SEC"]) as _r:
                    _jj = _j.loads(_r.read().decode("utf-8"))
                _lp = float((_jj.get("data") or {}).get("amount") or 0) or None
                if _lp and _lp > 0:
                    price = _lp
            except Exception:
                pass


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


            # --- MANUAL BALANCES OVERRIDE (tracking only) ---
            try:
                s = _load_settings()
                rp = float((s or {}).get("reco_percent") or 0.0)
                rp = max(0.0, min(1.0, rp))
                mc = (s or {}).get("manual_cash_usd")
                mb_usd = (s or {}).get("manual_btc_usd")
                mb_qty = (s or {}).get("manual_btc_qty")
                # prefer qty if provided; else usd value
                if action in ("BUY", "SELL") and rp > 0:
                    if action == "BUY" and mc is not None:
                        recommended_usd = round(float(mc) * rp, 2)
                    elif action == "SELL":
                        if mb_qty is not None and price and float(price) > 0:
                            recommended_usd = round(float(mb_qty) * float(price) * rp, 2)
                        elif mb_usd is not None:
                            recommended_usd = round(float(mb_usd) * rp, 2)
            except Exception:
                pass
            # --- END MANUAL BALANCES OVERRIDE ---

            return self._send_json(200, {
                "ok": True,
                "action": action,
                "symbol": symbol,
                "price": price,
                "engine_price": engine_price,
                "recommended_usd": recommended_usd,

                "recommended_btc": recommended_btc
            })

        if path == "/confirm/status":
            c = _read_json(CONFIRM_PATH)
            return self._send_json(200, {"ok": True, "confirm_path": CONFIRM_PATH, "confirm": c})


        if path == "/alerts":
            # Ensure alerts.env exists with defaults (first run)
            try:
                if not os.path.exists(ALERTS_ENV_PATH):
                    _write_env_kv(ALERTS_ENV_PATH, {
                        "ENABLED": 1,
                        "NOTIFY": 1,
                        "VIBRATE": 1,
                        "SPEAK": 1,
                        "POLL_SEC": 10,
                        "REPEAT_SEC": 0,
                        "QUIET_MODE": 0,
                        "QUIET_START": "22:00",
                        "QUIET_END": "07:00",
                        "ALLOW_QUIET_NOTIFY": 0,
                        "ALLOW_QUIET_VIBRATE": 0,
                        "ALLOW_QUIET_SPEAK": 0,
                    })
            except Exception:
                pass

            cfg = _read_env_kv(ALERTS_ENV_PATH) or {}
            eff = _effective_now(cfg)
            return self._send_json(200, {
                "ok": True,
                "alerts_env_path": ALERTS_ENV_PATH,
                "alerts": cfg,
                **eff
            })

        if path == "/settings":

            s = _load_settings()
            if isinstance(s, dict) and "pos_side" not in s:
                s["pos_side"] = "FLAT"
            if isinstance(s, dict) and "pos_qty" not in s:
                s["pos_qty"] = None
            if isinstance(s, dict) and "pos_entry_price" not in s:
                s["pos_entry_price"] = None
            if isinstance(s, dict) and "intel_profile" not in s:
                s["intel_profile"] = EZ_INTEL_ACTIVE_PROFILE

            # --- battery / polling settings (UI polling cadence; beginner-friendly presets) ---
            if isinstance(s, dict) and "poll_mode" not in s:
                s["poll_mode"] = "balanced"   # balanced | saver | fast
            if isinstance(s, dict) and "poll_signal_sec" not in s:
                s["poll_signal_sec"] = 5
            if isinstance(s, dict) and "poll_reco_sec" not in s:
                s["poll_reco_sec"] = 10
            if isinstance(s, dict) and "poll_intel_sec" not in s:
                s["poll_intel_sec"] = 30
            if isinstance(s, dict) and "poll_health_sec" not in s:
                s["poll_health_sec"] = 15
            if isinstance(s, dict) and "bg_multiplier" not in s:
                s["bg_multiplier"] = 4   # when screen hidden, multiply polling intervals
            if isinstance(s, dict) and "pause_when_hidden" not in s:
                s["pause_when_hidden"] = 0  # 1 = fully pause updates when hidden
            # --- end battery / polling settings ---
            return self._send_json(200, {"ok": True, "settings_path": SETTINGS_PATH, "settings": s})



        if path == "/portfolio":
            try:
                # Read current settings and build portfolio snapshot
                _st = _load_settings() or {}
                _st = _portfolio_defaults(dict(_st or {}))
                return self._send_json(200, _build_portfolio_payload(_st))
            except Exception as e:
                return self._send_json(500, {"ok": False, "error": "portfolio_failed", "detail": str(e)})

        # EZ_OPPORTUNITIES_ROUTE_V1
        if path == "/opportunities":
            qs = parse_qs((urlparse(self.path).query or ""))
            try:
                interval = int((qs.get("interval") or ["5"])[0])
            except Exception:
                interval = 5
            try:
                limit = int((qs.get("limit") or ["5"])[0])
            except Exception:
                limit = 5

            # Watchlist from settings (fallback to DEFAULT_PORTFOLIO_SYMBOLS if present)
            try:
                _st = _load_settings() or {}
            except Exception:
                _st = {}
            try:
                raw_syms = list(_st.get("portfolio_symbols") or [])
            except Exception:
                raw_syms = []
            if not raw_syms:
                try:
                    raw_syms = list(DEFAULT_PORTFOLIO_SYMBOLS[:])
                except Exception:
                    raw_syms = ["BTC-USD","ETH-USD","SOL-USD","DOGE-USD"]

            PAIR = {
                "BTC-USD": "XBTUSD",
                "ETH-USD": "ETHUSD",
                "SOL-USD": "SOLUSD",
                "XRP-USD": "XRPUSD",
                "DOGE-USD": "DOGEUSD",
                "ADA-USD": "ADAUSD",
                "AVAX-USD": "AVAXUSD",
                "LINK-USD": "LINKUSD",
                "MATIC-USD": "MATICUSD",
                "DOT-USD": "DOTUSD",
                "LTC-USD": "LTCUSD",
                "BCH-USD": "BCHUSD",
                "UNI-USD": "UNIUSD",
                "AAVE-USD": "AAVEUSD",
                "ATOM-USD": "ATOMUSD",
            }

            def _norm(sym: str) -> str:
                try:
                    sym = (sym or "").strip().upper()
                except Exception:
                    return "BTC-USD"
                if sym in ("BTCUSD","XBTUSD","XBT-USD","BTC-USD"): return "BTC-USD"
                if sym in ("ETHUSD","ETH-USD"): return "ETH-USD"
                if sym in ("SOLUSD","SOL-USD"): return "SOL-USD"
                if sym in ("DOGEUSD","DOGE-USD"): return "DOGE-USD"
                if sym in PAIR: return sym
                return "BTC-USD"

            # Deduped watchlist AFTER normalization (preserve order)
            syms = []
            seen = set()
            for x in raw_syms:
                y = _norm(x)
                if y not in seen:
                    seen.add(y)
                    syms.append(y)

            def _rsi(closes, period=14):
                if not closes or len(closes) < period + 1:
                    return None
                gains = []
                losses = []
                for i in range(1, len(closes)):
                    d = closes[i] - closes[i-1]
                    if d >= 0:
                        gains.append(d); losses.append(0.0)
                    else:
                        gains.append(0.0); losses.append(-d)
                g = sum(gains[-period:]) / period
                l = sum(losses[-period:]) / period
                if l == 0:
                    return 100.0
                rs = g / l
                return 100.0 - (100.0 / (1.0 + rs))

            def _fetch_ohlc(pair, interval_min, timeout_sec=6.0):
                import urllib.request, json
                url = f"https://api.kraken.com/0/public/OHLC?pair={pair}&interval={int(interval_min)}"
                raw = urllib.request.urlopen(url, timeout=timeout_sec).read().decode("utf-8", "replace")
                j = json.loads(raw) if raw else {}
                res = (j or {}).get("result") or {}
                if not isinstance(res, dict) or not res:
                    return []
                ohlc = None
                for k, v in res.items():
                    if k == "last":
                        continue
                    if isinstance(v, list):
                        ohlc = v
                        break
                if not ohlc:
                    return []
                out = []
                for row in ohlc:
                    try:
                        out.append({
                            "time": int(row[0]),
                            "open": float(row[1]),
                            "high": float(row[2]),
                            "low": float(row[3]),
                            "close": float(row[4]),
                        })
                    except Exception:
                        continue
                return out

            # Build results, one per symbol (keep best score)
            best = {}
            skipped = []  # debug: symbols skipped + why

            for sym in syms:
                pair = PAIR.get(sym)
                if not pair:
                    skipped.append({"symbol": sym, "why": "no_pair_mapping"})
                    continue
                try:
                    candles = _fetch_ohlc(pair, interval, timeout_sec=EZ_INTEL_GUARDRAILS.get("HTTP_TIMEOUT_SEC", 6))
                    if not candles:
                        skipped.append({"symbol": sym, "why": "no_candles"})
                        continue
                    closes = [c["close"] for c in candles][-120:]
                    last = closes[-1]
                    rsi = _rsi(closes, 14)

                    action = "HOLD"
                    score = 0.0
                    reason = "neutral"

                    if rsi is not None and rsi < 35:
                        action = "BUY"
                        score = float(35 - rsi)
                        reason = f"RSI {rsi:.1f} (oversold)"
                    elif rsi is not None and rsi > 65:
                        action = "SELL"
                        score = float(rsi - 65)
                        reason = f"RSI {rsi:.1f} (overbought)"

                    try:
                        base = closes[-6]
                        if base:
                            move = (last - base) / base * 100.0
                            if action == "BUY" and move < 0:
                                score += min(10.0, abs(move))
                            if action == "SELL" and move > 0:
                                score += min(10.0, abs(move))
                    except Exception:
                        pass


                    o = {
                        "symbol": sym,
                        "action": action,
                        "score": round(score, 3),
                        "price": last,
                        "rsi": None if rsi is None else round(float(rsi), 3),
                        "reason": reason,

                    }
                    prev = best.get(sym)
                    if (prev is None) or (float(o.get("score") or 0.0) > float(prev.get("score") or 0.0)):
                        best[sym] = o
                except Exception:
                    continue

            opps = list(best.values())
            opps.sort(key=lambda o: (0 if o["action"] in ("BUY","SELL") else 1, -float(o.get("score") or 0.0)))

            if limit < 1: limit = 1
            if limit > 25: limit = 25
            return self._send_json(200, {
                "ok": True,
                "interval": interval,
                "count": len(opps),
                "top": opps[:limit],
                  "skipped": skipped,
            })







        # --- Chart endpoint: live price (read-only) ---
        # --- Chart endpoint: OHLC candles (read-only) ---
        # --- Chart endpoint: live price (read-only) ---
        if path == "/price":
            qs = parse_qs((urlparse(self.path).query or ""))
            sym = (qs.get("symbol") or ["BTC-USD"])[0]
            px = _ez_live_kraken_price_symbol(sym, timeout_sec=2.5)
            return self._send_json(200, {"ok": bool(px is not None), "symbol": _ez_norm_symbol(sym), "price": px, "ts_ms": int(time.time() * 1000)})
        # --- Chart endpoint: OHLC candles (read-only) ---

        # EZ_SIGNALS_ROUTE_V1
        if path == "/signals":
            qs = parse_qs((urlparse(self.path).query or ""))
            try:
                interval = int((qs.get("interval") or ["5"])[0])
            except Exception:
                interval = 5
            try:
                since = int((qs.get("since") or ["0"])[0]) or None
            except Exception:
                since = None

            # Use the same candle source as /ohlc (Kraken helper) so chart + signals stay consistent
            sym = (qs.get("symbol") or ["BTC-USD"])[0]
            candles = _ez_kraken_ohlc_symbol(sym, interval_min=interval, since=since, timeout_sec=EZ_INTEL_GUARDRAILS.get("HTTP_TIMEOUT_SEC", 6))
            signals = _ez_build_signals_from_candles(candles)
            return self._send_json(200, {"ok": True, "interval": interval, "signals": signals})

        if path == "/ohlc":
            qs = parse_qs((urlparse(self.path).query or ""))
            try:
                interval = int((qs.get("interval") or ["5"])[0])
            except Exception:
                interval = 5
            try:
                since = int((qs.get("since") or ["0"])[0]) or None
            except Exception:
                since = None
            sym = (qs.get("symbol") or ["BTC-USD"])[0]
            candles = _ez_kraken_ohlc_symbol(sym, interval_min=interval, since=since, timeout_sec=EZ_INTEL_GUARDRAILS.get("HTTP_TIMEOUT_SEC", 6))
            return self._send_json(200, {"ok": True, "interval": interval, "candles": candles})

        return self._send_json(404, {"ok": False, "error": "not found", "paths": ["/health", "/decision", "/signal", "/confirm", "/confirm/status", "/settings", "/alerts", "/portfolio", "/ui/*", "/"]})


    def do_POST(self):
        # --- ALERTS (POST) --- (END_ALERTS_POST_V70)
        try:
            _p = self.path.split("?", 1)[0]
        except Exception:
            _p = self.path

        if _p == "/alerts":
            # Read JSON safely (works across variants)
            body = {}
            try:
                body = self._read_json_body() or {}
            except Exception:
                try:
                    body = self._read_json() or {}
                except Exception:
                    body = {}

            # Defaults if file is missing/empty
            cfg = _read_env_kv(ALERTS_ENV_PATH) or {}
            if not cfg:
                cfg = {
                    "ENABLED": 1,
                    "NOTIFY": 1,
                    "VIBRATE": 1,
                    "SPEAK": 1,
                    "POLL_SEC": 10,
                    "REPEAT_SEC": 0,
                    "QUIET_MODE": 0,
                    "QUIET_START": "22:00",
                    "QUIET_END": "07:00",
                    "ALLOW_QUIET_NOTIFY": 0,
                    "ALLOW_QUIET_VIBRATE": 0,
                    "ALLOW_QUIET_SPEAK": 0,
                }

            def b(v, default):
                if v is None:
                    return default
                return 1 if bool(v) else 0

            def i(v, default):
                if v is None:
                    return default
                try:
                    return int(v)
                except Exception:
                    return default

            def t(v, default):
                if v is None:
                    return default
                v = str(v).strip()
                return v if v else default

            allow = body.get("allow_during_quiet") or {}

            # Apply updates (if omitted -> keep current)
            cfg["ENABLED"] = b(body.get("enabled"), cfg.get("ENABLED", 1))
            cfg["NOTIFY"]  = b(body.get("notify"),  cfg.get("NOTIFY", 1))
            cfg["VIBRATE"] = b(body.get("vibrate"), cfg.get("VIBRATE", 1))
            cfg["SPEAK"]   = b(body.get("speak"),   cfg.get("SPEAK", 1))

            cfg["POLL_SEC"]   = i(body.get("poll_sec"),   cfg.get("POLL_SEC", 10))
            cfg["REPEAT_SEC"] = i(body.get("repeat_sec"), cfg.get("REPEAT_SEC", 0))

            cfg["QUIET_MODE"]  = b(body.get("quiet_mode"), cfg.get("QUIET_MODE", 0))
            cfg["QUIET_START"] = t(body.get("quiet_start"), cfg.get("QUIET_START", "22:00"))
            cfg["QUIET_END"]   = t(body.get("quiet_end"),   cfg.get("QUIET_END", "07:00"))

            cfg["ALLOW_QUIET_NOTIFY"]  = b(allow.get("notify"),  cfg.get("ALLOW_QUIET_NOTIFY", 0))
            cfg["ALLOW_QUIET_VIBRATE"] = b(allow.get("vibrate"), cfg.get("ALLOW_QUIET_VIBRATE", 0))
            cfg["ALLOW_QUIET_SPEAK"]   = b(allow.get("speak"),   cfg.get("ALLOW_QUIET_SPEAK", 0))

            try:
                _write_env_kv(ALERTS_ENV_PATH, cfg)
            except Exception:
                pass

            eff = _effective_now(cfg)
            return self._send_json(200, {
                "ok": True,
                "alerts_env_path": ALERTS_ENV_PATH,
                "alerts": cfg,
                **eff
            })
        # --- END ALERTS (POST) ---

        path = urlparse(self.path).path

        # --- EZ Alerts persist: POST /alerts ---
        if path == "/alerts":
            try:
                data = self._read_json() if hasattr(self, "_read_json") else {}
            except Exception:
                data = {}
            try:
                saved, ap = _ez_save_alerts(data if isinstance(data, dict) else {})
                return self._send_json(200, {"ok": True, "alerts_path": ap, "alerts": saved})
            except Exception as e:
                return self._send_json(500, {"ok": False, "error": "alerts save failed"})

        if path not in ("/confirm", "/settings", "/alerts"):
            return self._send_json(404, {"ok": False, "error": "not found"})

        # body json
        try:
            n = int(self.headers.get("Content-Length", "0"))
        except Exception:
            n = 0
        body = self.rfile.read(n) if n > 0 else b""
        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
            # Manual Average Price (USD) — single visible field
            try:
                v = (payload or {}).get('avg_price_usd', None)
                if v is not None and str(v).strip() != '':
                    fv = float(v)
                    if fv < 0: fv = 0.0
                    # store into settings dict later via payload passthrough
                    payload['avg_price_usd'] = fv
            except Exception:
                pass
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
    ensure_dirs()
    # Avoid "Address already in use" on quick restarts
    HTTPServer.allow_reuse_address = True
    httpd = HTTPServer((HOST, PORT), Handler)
    try:
        print(f"EZTrade server running on http://{HOST}:{PORT}")
    except Exception:
        pass
    httpd.serve_forever()

if __name__ == "__main__":
    main()
