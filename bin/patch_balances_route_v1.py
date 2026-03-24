from pathlib import Path
import re, sys

p = Path("app/server.py")
s = p.read_text("utf-8", errors="replace")

MARK = "EZ_BALANCES_ROUTE_V1"

# Anchor: we insert balances route right before the chart endpoints block
anchor = re.search(r'^\s*# --- Chart endpoint: live price \(read-only\) ---\s*$', s, flags=re.M)
if not anchor:
    print("PATCH FAILED: could not find chart anchor comment")
    sys.exit(1)

# If already patched, do nothing
if re.search(r'^\s*#\s*' + re.escape(MARK) + r'\s*$', s, flags=re.M):
    print("OK ✅ balances route already present")
    sys.exit(0)

# Determine route indentation from existing /price route
m_if = re.search(r'^(?P<ind>\s*)if path == "/price":\s*$', s, flags=re.M)
if not m_if:
    print('PATCH FAILED: could not find line: if path == "/price":')
    sys.exit(1)
IND = m_if.group("ind")

block = f'''
{IND}# {MARK}
{IND}if path == "/balances":
{IND}    qs = parse_qs((urlparse(self.path).query or ""))
{IND}    # symbols=BTC-USD,ETH-USD,XRP-USD (optional)
{IND}    raw_syms = (qs.get("symbols") or [""])[0]
{IND}    syms = []
{IND}    if raw_syms:
{IND}        try:
{IND}            syms = [x.strip().upper() for x in raw_syms.split(",") if x.strip()]
{IND}        except Exception:
{IND}            syms = []

{IND}    # Load app state safely
{IND}    try:
{IND}        import os, json
{IND}        ap = globals().get("APP_STATE_PATH") or globals().get("APP_STATE_FILE") or ""
{IND}        if not ap:
{IND}            ap = os.path.join(os.path.expanduser("~"), "v71_app_data", "state.json")
{IND}        st = {{}}
{IND}        try:
{IND}            st = json.loads(Path(ap).read_text("utf-8", errors="replace"))
{IND}        except Exception:
{IND}            st = {{}}
{IND}    except Exception:
{IND}        st = {{}}

{IND}    # cash + holdings (support a couple layouts)
{IND}    cash = None
{IND}    try:
{IND}        cash = float(st.get("cash_usd"))
{IND}    except Exception:
{IND}        try:
{IND}            cash = float((st.get("balances") or {{}}).get("cash_usd"))
{IND}        except Exception:
{IND}            cash = 0.0

{IND}    holdings = {{}}
{IND}    try:
{IND}        holdings = dict(st.get("holdings") or {{}})
{IND}    except Exception:
{IND}        try:
{IND}            holdings = dict((st.get("balances") or {{}}).get("holdings") or {{}})
{IND}        except Exception:
{IND}            holdings = {{}}

{IND}    # If no symbols passed, default to holdings keys; else safe defaults
{IND}    if not syms:
{IND}        try:
{IND}            syms = [k.strip().upper() for k in holdings.keys() if isinstance(k, str)]
{IND}        except Exception:
{IND}            syms = []
{IND}    if not syms:
{IND}        syms = ["BTC-USD","ETH-USD","XRP-USD"]

{IND}    # Live prices (read-only)
{IND}    prices = {{}}
{IND}    get_px = globals().get("_ez_live_kraken_price_symbol")
{IND}    norm = globals().get("_ez_norm_symbol")
{IND}    for sym0 in syms:
{IND}        sym = sym0
{IND}        try:
{IND}            sym = norm(sym0) if callable(norm) else sym0
{IND}        except Exception:
{IND}            sym = sym0
{IND}        px = None
{IND}        try:
{IND}            if callable(get_px):
{IND}                px = get_px(sym, timeout_sec=2.5)
{IND}        except Exception:
{IND}            px = None
{IND}        prices[sym] = px

{IND}    # Total equity
{IND}    equity = float(cash or 0.0)
{IND}    for sym, amt in list(holdings.items()):
{IND}        try:
{IND}            a = float(amt)
{IND}        except Exception:
{IND}            continue
{IND}        px = prices.get(sym)
{IND}        if px is None:
{IND}            continue
{IND}        try:
{IND}            equity += a * float(px)
{IND}        except Exception:
{IND}            pass

{IND}    return self._send_json(200, {{
{IND}        "ok": True,
{IND}        "cash_usd": round(float(cash or 0.0), 2),
{IND}        "holdings": holdings,
{IND}        "prices": prices,
{IND}        "equity_usd": round(float(equity), 2),
{IND}        "ts_ms": int(time.time() * 1000),
{IND}    }})
'''

s = s[:anchor.start()] + block + "\n" + s[anchor.start():]
p.write_text(s, "utf-8")
print("OK ✅ Added /balances route")
