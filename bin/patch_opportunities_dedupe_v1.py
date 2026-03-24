from pathlib import Path
import re, sys

p = Path("app/server.py")
s = p.read_text("utf-8", errors="replace")

MARK = "EZ_OPPORTUNITIES_ROUTE_V1"

m = re.search(r'^\s*#\s*' + re.escape(MARK) + r'\s*$', s, flags=re.M)
if not m:
    print("PATCH FAILED: opportunities marker not found")
    sys.exit(1)

anchor = re.search(r'^\s*# --- Chart endpoint: live price \(read-only\) ---\s*$', s[m.start():], flags=re.M)
if not anchor:
    print("PATCH FAILED: chart anchor not found after opportunities marker")
    sys.exit(1)
anchor_start = m.start() + anchor.start()

# Determine indentation from existing /price route line
m_if = re.search(r'^(?P<ind>\s*)if path == "/price":\s*$', s, flags=re.M)
if not m_if:
    print('PATCH FAILED: could not find line: if path == "/price":')
    sys.exit(1)
IND = m_if.group("ind")

block = f'''
{IND}# {MARK}
{IND}if path == "/opportunities":
{IND}    qs = parse_qs((urlparse(self.path).query or ""))
{IND}    try:
{IND}        interval = int((qs.get("interval") or ["5"])[0])
{IND}    except Exception:
{IND}        interval = 5
{IND}    try:
{IND}        limit = int((qs.get("limit") or ["5"])[0])
{IND}    except Exception:
{IND}        limit = 5

{IND}    # Watchlist from settings (fallback to DEFAULT_PORTFOLIO_SYMBOLS if present)
{IND}    try:
{IND}        _st = _load_settings() or {{}}
{IND}    except Exception:
{IND}        _st = {{}}
{IND}    try:
{IND}        raw_syms = list(_st.get("portfolio_symbols") or [])
{IND}    except Exception:
{IND}        raw_syms = []
{IND}    if not raw_syms:
{IND}        try:
{IND}            raw_syms = list(DEFAULT_PORTFOLIO_SYMBOLS[:])
{IND}        except Exception:
{IND}            raw_syms = ["BTC-USD","ETH-USD","SOL-USD","DOGE-USD"]

{IND}    PAIR = {{
{IND}        "BTC-USD": "XBTUSD",
{IND}        "ETH-USD": "ETHUSD",
{IND}        "SOL-USD": "SOLUSD",
{IND}        "DOGE-USD": "DOGEUSD",
{IND}    }}

{IND}    def _norm(sym: str) -> str:
{IND}        try:
{IND}            sym = (sym or "").strip().upper()
{IND}        except Exception:
{IND}            return "BTC-USD"
{IND}        if sym in ("BTCUSD","XBTUSD","XBT-USD","BTC-USD"): return "BTC-USD"
{IND}        if sym in ("ETHUSD","ETH-USD"): return "ETH-USD"
{IND}        if sym in ("SOLUSD","SOL-USD"): return "SOL-USD"
{IND}        if sym in ("DOGEUSD","DOGE-USD"): return "DOGE-USD"
{IND}        if sym in PAIR: return sym
{IND}        return "BTC-USD"

{IND}    # Deduped watchlist AFTER normalization (preserve order)
{IND}    syms = []
{IND}    seen = set()
{IND}    for x in raw_syms:
{IND}        y = _norm(x)
{IND}        if y not in seen:
{IND}            seen.add(y)
{IND}            syms.append(y)

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
{IND}        import urllib.request, json
{IND}        url = f"https://api.kraken.com/0/public/OHLC?pair={{pair}}&interval={{int(interval_min)}}"
{IND}        raw = urllib.request.urlopen(url, timeout=timeout_sec).read().decode("utf-8", "replace")
{IND}        j = json.loads(raw) if raw else {{}}
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

{IND}    # Build results, one per symbol (keep best score)
{IND}    best = {{}}
{IND}    for sym in syms:
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

{IND}            try:
{IND}                base = closes[-6]
{IND}                if base:
{IND}                    move = (last - base) / base * 100.0
{IND}                    if action == "BUY" and move < 0:
{IND}                        score += min(10.0, abs(move))
{IND}                    if action == "SELL" and move > 0:
{IND}                        score += min(10.0, abs(move))
{IND}            except Exception:
{IND}                pass

{IND}            o = {{
{IND}                "symbol": sym,
{IND}                "action": action,
{IND}                "score": round(score, 3),
{IND}                "price": last,
{IND}                "rsi": None if rsi is None else round(float(rsi), 3),
{IND}                "reason": reason,
{IND}            }}
{IND}            prev = best.get(sym)
{IND}            if (prev is None) or (float(o.get("score") or 0.0) > float(prev.get("score") or 0.0)):
{IND}                best[sym] = o
{IND}        except Exception:
{IND}            continue

{IND}    opps = list(best.values())
{IND}    opps.sort(key=lambda o: (0 if o["action"] in ("BUY","SELL") else 1, -float(o.get("score") or 0.0)))

{IND}    if limit < 1: limit = 1
{IND}    if limit > 25: limit = 25
{IND}    return self._send_json(200, {{
{IND}        "ok": True,
{IND}        "interval": interval,
{IND}        "count": len(opps),
{IND}        "top": opps[:limit],
{IND}    }})
'''

s2 = s[:m.start()] + block + "\n" + s[anchor_start:]
p.write_text(s2, "utf-8")
print("OK ✅ patched opportunities: dedupe watchlist + dedupe results")
