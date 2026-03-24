from pathlib import Path
import re

p = Path("app/server.py")
s = p.read_text("utf-8", errors="replace")

# 1) Insert helpers before _ez_kraken_ohlc()
if "EZ_SYMBOL_ROUTING_V2" not in s:
    m = re.search(r"^def _ez_kraken_ohlc\(", s, flags=re.M)
    if not m:
        raise SystemExit("PATCH FAILED: could not find def _ez_kraken_ohlc(")

    helpers = '''
# EZ_SYMBOL_ROUTING_V2 (crypto-only)
_KRAKEN_PAIR = {
    "BTC-USD": "XBTUSD",
    "ETH-USD": "ETHUSD",
    "SOL-USD": "SOLUSD",
    "DOGE-USD": "DOGEUSD",
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
'''
    s = s[:m.start()] + helpers + "\n" + s[m.start():]

# 2) Patch /price block using regex (indent-safe)
price_pat = re.compile(
    r'(?m)^(?P<ind>[ \t]*)if path == "/price":\s*\n'
    r'(?P<ind2>[ \t]*)px\s*=\s*_ez_live_kraken_btc_usd\(timeout_sec=2\.5\)\s*\n'
    r'(?P<ind3>[ \t]*)return\s+self\._send_json\(200,\s*\{"ok":\s*bool\(px is not None\),\s*"price":\s*px,\s*"ts_ms":\s*int\(time\.time\(\)\s*\*\s*1000\)\}\)\s*\n'
)
m = price_pat.search(s)
if not m:
    raise SystemExit("PATCH FAILED: could not match /price block with regex")

ind = m.group("ind")
ind2 = m.group("ind2") or (ind + "    ")
# keep same inner indent as original px line
repl = (
    f'{ind}if path == "/price":\n'
    f'{ind2}qs = parse_qs((urlparse(self.path).query or ""))\n'
    f'{ind2}sym = (qs.get("symbol") or ["BTC-USD"])[0]\n'
    f'{ind2}px = _ez_live_kraken_price_symbol(sym, timeout_sec=2.5)\n'
    f'{ind2}return self._send_json(200, {{"ok": bool(px is not None), "symbol": _ez_norm_symbol(sym), "price": px, "ts_ms": int(time.time() * 1000)}})\n'
)
s = price_pat.sub(repl, s, count=1)

# 3) Patch candles line in /signals and /ohlc (two occurrences), preserve indent
cand_pat = re.compile(
    r'(?m)^(?P<ind>[ \t]*)candles\s*=\s*_ez_kraken_ohlc\(interval_min=interval,\s*since=since,\s*timeout_sec=EZ_INTEL_GUARDRAILS\.get\("HTTP_TIMEOUT_SEC",\s*6\)\)\s*$'
)
hits = list(cand_pat.finditer(s))
if len(hits) < 2:
    raise SystemExit(f"PATCH FAILED: expected 2 candles lines, found {len(hits)}")

def repl_cand(m):
    ind = m.group("ind")
    return (
        f'{ind}sym = (qs.get("symbol") or ["BTC-USD"])[0]\n'
        f'{ind}candles = _ez_kraken_ohlc_symbol(sym, interval_min=interval, since=since, timeout_sec=EZ_INTEL_GUARDRAILS.get("HTTP_TIMEOUT_SEC", 6))'
    )

# Replace first two occurrences only
s, n1 = cand_pat.subn(repl_cand, s, count=2)
if n1 != 2:
    raise SystemExit(f"PATCH FAILED: candles replace count was {n1}, expected 2")

p.write_text(s, "utf-8")
print("OK ✅ Applied EZ_SYMBOL_ROUTING_V2 + patched /price /signals /ohlc")
