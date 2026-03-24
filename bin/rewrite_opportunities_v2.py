from pathlib import Path
import re, sys

p = Path("app/server.py")
s = p.read_text("utf-8", errors="replace")

MARK = "EZ_OPPORTUNITIES_ROUTE_V1"

# Find chart anchor comment (we insert opportunities right before this)
anchor = re.search(r'^\s*# --- Chart endpoint: live price \(read-only\) ---\s*$', s, flags=re.M)
if not anchor:
    print("PATCH FAILED: could not find chart anchor comment")
    sys.exit(1)

# If an old/broken opportunities block exists, remove everything from its marker up to the chart anchor
m = re.search(r'^\s*#\s*' + re.escape(MARK) + r'\s*$', s, flags=re.M)
if m:
    s = s[:m.start()] + s[anchor.start():]
    anchor = re.search(r'^\s*# --- Chart endpoint: live price \(read-only\) ---\s*$', s, flags=re.M)
    if not anchor:
        print("PATCH FAILED: anchor missing after removal")
        sys.exit(1)

# Determine route indentation by looking for the existing /price route line
m_if = re.search(r'^(?P<ind>\s*)if path == "/price":\s*$', s, flags=re.M)
if not m_if:
    print('PATCH FAILED: could not find line: if path == "/price":')
    sys.exit(1)

IND = m_if.group("ind")  # exact indentation used by other routes

block = f'''
{IND}# {MARK}
{IND}if path == "/opportunities":
{IND}    qs = parse_qs((urlparse(self.path).query or ""))
{IND}    try:
{IND}        interval = int((qs.get("interval") or ["5"])[0])
{IND}    except Exception:
{IND}        interval = 5
{IND}    try:
{IND}        limit = int((qs.get("limit") or ["6"])[0])
{IND}    except Exception:
{IND}        limit = 6
{IND}    if limit < 1: limit = 1
{IND}    if limit > 25: limit = 25

{IND}    # Settings + watchlist
{IND}    try:
{IND}        _st = _load_settings() or {{}}
{IND}    except Exception:
{IND}        _st = {{}}

{IND}    syms = []
{IND}    try:
{IND}        syms = list(_st.get("portfolio_symbols") or [])
{IND}    except Exception:
{IND}        syms = []
{IND}    if not syms:
{IND}        try:
{IND}            syms = list(DEFAULT_PORTFOLIO_SYMBOLS[:])
{IND}        except Exception:
{IND}            syms = ["BTC-USD","ETH-USD","SOL-USD","XRP-USD","DOGE-USD"]

{IND}    # Tactical pool (Ben set to 5000)
{IND}    try:
{IND}        pool = float(_st.get("tactical_pool_usd") or 0.0)
{IND}    except Exception:
{IND}        pool = 0.0

{IND}    # Read holdings from app_state (paper now; real later)
{IND}    holdings = {{}}
{IND}    try:
{IND}        import json as _json
{IND}        from pathlib import Path as _Path
{IND}        _ap = _Path(APP_STATE_PATH)
{IND}        if _ap.exists():
{IND}            _aj = _json.loads(_ap.read_text("utf-8", errors="replace"))
{IND}            if isinstance(_aj, dict):
{IND}                _h = _aj.get("holdings") or {{}}
{IND}                if isinstance(_h, dict):
{IND}                    holdings = _h
{IND}    except Exception:
{IND}        holdings = {{}}

{IND}    # Kraken pairs (crypto-only)
{IND}    PAIR = {{
{IND}        "BTC-USD": "XBTUSD",
{IND}        "ETH-USD": "ETHUSD",
{IND}        "SOL-USD": "SOLUSD",
{IND}        "XRP-USD": "XRPUSD",
{IND}        "DOGE-USD": "DOGEUSD",
{IND}        "ADA-USD": "ADAUSD",
{IND}    }}

{IND}    def _norm(sym: str) -> str:
{IND}        try:
{IND}            sym = (sym or "").strip().upper()
{IND}        except Exception:
{IND}            return "BTC-USD"
{IND}        if sym in ("BTCUSD","XBTUSD","XBT-USD"): return "BTC-USD"
{IND}        if sym in ("ETHUSD","ETH-USD"): return "ETH-USD"
{IND}        if sym in ("SOLUSD","SOL-USD"): return "SOL-USD"
{IND}        if sym in ("XRPUSD","XRP-USD"): return "XRP-USD"
{IND}        if sym in ("DOGEUSD","DOGE-USD"): return "DOGE-USD"
{IND}        if sym in ("ADAUSD","ADA-USD"): return "ADA-USD"
{IND}        if sym in PAIR: return sym
{IND}        return "BTC-USD"

{IND}    def _rsi(closes, period=14):
{IND}        if not closes or len(closes) < period + 1:
{IND}            return None
{IND}        gains = []
{IND}        losses = []
{IND}        for i in range(1, len(closes)):
{IND}            d = closes[i] - closes[i-1]
{IND}            if d >= 0:
{IND}                gains.append(d); losses.append(0.0)
{IND}            else:
{IND}                gains.append(0.0); losses.append(-d)
{IND}        g = sum(gains[-period:]) / period
{IND}        l = sum(losses[-period:]) / period
{IND}        if l == 0:
{IND}            return 100.0
{IND}        rs = g / l
{IND}        return 100.0 - (100.0 / (1.0 + rs))

{IND}    def _fetch_ohlc(pair, interval_min, timeout_sec=6.0):
{IND}        import urllib.request as _u, json as _j
{IND}        url = f"https://api.kraken.com/0/public/OHLC?pair={{pair}}&interval={{int(interval_min)}}"
{IND}        raw = _u.urlopen(url, timeout=timeout_sec).read().decode("utf-8", "replace")
{IND}        j = _j.loads(raw) if raw else {{}}
{IND}        res = (j or {{}}).get("result") or {{}}
{IND}        if not isinstance(res, dict) or not res:
{IND}            return []
{IND}        ohlc = None
{IND}        for k, v in res.items():
{IND}            if k == "last":
{IND}                continue
{IND}            if isinstance(v, list):
{IND}                ohlc = v
{IND}                break
{IND}        if not ohlc:
{IND}            return []
{IND}        out = []
{IND}        for row in ohlc:
{IND}            try:
{IND}                out.append({{
{IND}                    "time": int(row[0]),
{IND}                    "open": float(row[1]),
{IND}                    "high": float(row[2]),
{IND}                    "low": float(row[3]),
{IND}                    "close": float(row[4]),
{IND}                }})
{IND}            except Exception:
{IND}                continue
{IND}        return out

{IND}    def _alloc_pct(score: float) -> float:
{IND}        # Simple sizing tiers (easy to tune later)
{IND}        try:
{IND}            sc = float(score or 0.0)
{IND}        except Exception:
{IND}            sc = 0.0
{IND}        if sc >= 10: return 0.60
{IND}        if sc >= 6:  return 0.40
{IND}        if sc >= 3:  return 0.25
{IND}        if sc > 0:   return 0.15
{IND}        return 0.0

{IND}    opps = []
{IND}    for sym0 in syms:
{IND}        sym = _norm(sym0)
{IND}        pair = PAIR.get(sym)
{IND}        if not pair:
{IND}            continue
{IND}        try:
{IND}            candles = _fetch_ohlc(pair, interval, timeout_sec=EZ_INTEL_GUARDRAILS.get("HTTP_TIMEOUT_SEC", 6))
{IND}            if not candles:
{IND}                continue
{IND}            closes = [c["close"] for c in candles][-120:]
{IND}            last = closes[-1]
{IND}            rsi = _rsi(closes, 14)

{IND}            action = "HOLD"
{IND}            score = 0.0
{IND}            reason = "neutral"

{IND}            if rsi is not None and rsi < 35:
{IND}                action = "BUY"
{IND}                score = float(35 - rsi)
{IND}                reason = f"RSI {{rsi:.1f}} (oversold)"
{IND}            elif rsi is not None and rsi > 65:
{IND}                action = "SELL"
{IND}                score = float(rsi - 65)
{IND}                reason = f"RSI {{rsi:.1f}} (overbought)"

{IND}            # Holdings + sizing (always return fields)
{IND}            try:
{IND}                holding_qty = float((holdings or {{}}).get(sym) or 0.0)
{IND}            except Exception:
{IND}                holding_qty = 0.0
{IND}            try:
{IND}                est_value_usd = float(holding_qty) * float(last) if (holding_qty and last) else 0.0
{IND}            except Exception:
{IND}                est_value_usd = 0.0

{IND}            recommended_usd = 0.0
{IND}            recommended_qty = 0.0
{IND}            try:
{IND}                if action == "BUY":
{IND}                    pct = _alloc_pct(score)
{IND}                    recommended_usd = float(pool) * float(pct)
{IND}                    if last and recommended_usd > 0:
{IND}                        recommended_qty = float(recommended_usd) / float(last)
{IND}                elif action == "SELL":
{IND}                    # LOCKED_UNTIL_EXIT: sell what you hold (for now)
{IND}                    recommended_qty = float(holding_qty)
{IND}                    if last and recommended_qty > 0:
{IND}                        recommended_usd = float(recommended_qty) * float(last)
{IND}            except Exception:
{IND}                pass

{IND}            opps.append({{
{IND}                "symbol": sym,
{IND}                "action": action,
{IND}                "score": round(float(score), 3),
{IND}                "price": float(last),
{IND}                "rsi": None if rsi is None else round(float(rsi), 3),
{IND}                "reason": reason,
{IND}                "holding_qty": round(float(holding_qty), 10),
{IND}                "est_value_usd": round(float(est_value_usd), 4),
{IND}                "recommended_usd": round(float(recommended_usd), 4),
{IND}                "recommended_qty": round(float(recommended_qty), 10),
{IND}            }})
{IND}        except Exception:
{IND}            continue

{IND}    opps.sort(key=lambda o: (0 if o["action"] in ("BUY","SELL") else 1, -float(o.get("score") or 0.0)))
{IND}    return self._send_json(200, {{
{IND}        "ok": True,
{IND}        "interval": interval,
{IND}        "count": len(opps),
{IND}        "top": opps[:limit],
{IND}    }})
'''

# Insert block right before the chart anchor comment
s = s[:anchor.start()] + block + "\n" + s[anchor.start():]
p.write_text(s, "utf-8")
print("OK ✅ opportunities route rewritten (V2) with sizing fields + XRP.")
