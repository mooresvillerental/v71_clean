from pathlib import Path
import re

p = Path("app/server.py")
s = p.read_text("utf-8", errors="replace")

MARK = "EZ_OPPORTUNITIES_ROUTE_V1"
if MARK in s:
    print("SKIP ✅ opportunities route already present")
    raise SystemExit(0)

# Insert route right before the chart endpoints comment (stable anchor in your file)
anchor = re.search(r'^\s*# --- Chart endpoint: live price \(read-only\) ---\s*$', s, flags=re.M)
if not anchor:
    raise SystemExit("PATCH FAILED: could not find chart endpoint anchor comment")

inject = r'''
          # {MARK}
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

              # Read portfolio/watchlist from settings (fallback to DEFAULT_PORTFOLIO_SYMBOLS if present)
              try:
                  _st = _load_settings() or {{}}
              except Exception:
                  _st = {{}}
              syms = []
              try:
                  syms = list(_st.get("portfolio_symbols") or [])
              except Exception:
                  syms = []
              if not syms:
                  try:
                      syms = list(DEFAULT_PORTFOLIO_SYMBOLS[:])
                  except Exception:
                      syms = ["BTC-USD","ETH-USD","SOL-USD","DOGE-USD"]

              # Kraken pair mapping (crypto-only for now)
              PAIR = {{
                  "BTC-USD": "XBTUSD",
                  "ETH-USD": "ETHUSD",
                  "SOL-USD": "SOLUSD",
                  "DOGE-USD": "DOGEUSD",
              }}

              def _norm(sym: str) -> str:
                  try:
                      sym = (sym or "").strip().upper()
                  except Exception:
                      return "BTC-USD"
                  if sym in ("BTCUSD","XBTUSD","XBT-USD"): return "BTC-USD"
                  if sym in ("ETHUSD","ETH-USD"): return "ETH-USD"
                  if sym in ("SOLUSD","SOL-USD"): return "SOL-USD"
                  if sym in ("DOGEUSD","DOGE-USD"): return "DOGE-USD"
                  if sym in PAIR: return sym
                  return "BTC-USD"

              def _rsi(closes, period=14):
                  # simple RSI (Wilder-like smoothing not required for our ranking)
                  if not closes or len(closes) < period + 1:
                      return None
                  gains = []
                  losses = []
                  for i in range(1, len(closes)):
                      d = closes[i] - closes[i-1]
                      if d >= 0:
                          gains.append(d)
                          losses.append(0.0)
                      else:
                          gains.append(0.0)
                          losses.append(-d)
                  # last 'period' deltas
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
                  j = json.loads(raw) if raw else {{}}
                  res = (j or {{}}).get("result") or {{}}
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
                          out.append({{
                              "time": int(row[0]),
                              "open": float(row[1]),
                              "high": float(row[2]),
                              "low": float(row[3]),
                              "close": float(row[4]),
                          }})
                      except Exception:
                          continue
                  return out

              opps = []
              for sym0 in syms:
                  sym = _norm(sym0)
                  pair = PAIR.get(sym)
                  if not pair:
                      continue
                  try:
                      candles = _fetch_ohlc(pair, interval, timeout_sec=EZ_INTEL_GUARDRAILS.get("HTTP_TIMEOUT_SEC", 6))
                      if not candles:
                          continue
                      closes = [c["close"] for c in candles][-120:]
                      last = closes[-1]
                      rsi = _rsi(closes, 14)

                      # Simple opportunity scoring:
                      # BUY bias when RSI < 35, SELL bias when RSI > 65.
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

                      # Add a little momentum boost using recent move %
                      try:
                          base = closes[-6]  # last ~5 candles ago
                          if base:
                              move = (last - base) / base * 100.0
                              # favor mean reversion: if oversold and dropping, boost; if overbought and rising, boost
                              if action == "BUY" and move < 0:
                                  score += min(10.0, abs(move))
                              if action == "SELL" and move > 0:
                                  score += min(10.0, abs(move))
                      except Exception:
                          pass

                      opps.append({{
                          "symbol": sym,
                          "action": action,
                          "score": round(score, 3),
                          "price": last,
                          "rsi": None if rsi is None else round(float(rsi), 3),
                          "reason": reason,
                      }})
                  except Exception:
                      continue

              # Sort best first: BUY/SELL with higher score; HOLDs sink
              opps.sort(key=lambda o: (0 if o["action"] in ("BUY","SELL") else 1, -float(o.get("score") or 0.0)))

              if limit < 1: limit = 1
              if limit > 25: limit = 25
              return self._send_json(200, {{
                  "ok": True,
                  "interval": interval,
                  "count": len(opps),
                  "top": opps[:limit],
              }})
'''.replace("{MARK}", MARK)

s2 = s[:anchor.start()] + inject + "\n" + s[anchor.start():]
p.write_text(s2, "utf-8")
print("OK ✅ Added /opportunities endpoint")
