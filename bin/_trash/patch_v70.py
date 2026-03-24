import re, sys, json

PATH = "v70_app_ready_pro.py"

with open(PATH, "r", encoding="utf-8") as f:
    src = f.read()

def must_find(pattern: str):
    m = re.search(pattern, src, flags=re.M)
    if not m:
        raise SystemExit(f"Patch failed: pattern not found: {pattern}")
    return m

# 1) Add DEFAULT_STATE["cost_basis"]
# Insert '"cost_basis": {},' right after '"holdings": {},'
src2 = re.sub(
    r'("holdings"\s*:\s*\{\}\s*,[^\n]*\n)',
    r'\1    "cost_basis": {},          # per-symbol cost basis (total_cost_usd, total_qty)\n',
    src,
    count=1
)
if src2 == src:
    raise SystemExit("Patch failed: could not inject DEFAULT_STATE cost_basis")
src = src2

# 2) Inject cost-basis helper functions right before paper_buy
anchor = must_find(r'^def paper_buy\(').start()
helpers = r'''
# =========================
# COST BASIS (per-symbol)
# =========================
def _cb_get(state: dict, symbol: str) -> dict:
    cb = state.get("cost_basis", {})
    if not isinstance(cb, dict):
        cb = {}
    rec = cb.get(symbol)
    if not isinstance(rec, dict):
        rec = {"total_cost_usd": 0.0, "total_qty": 0.0}
    # normalize
    rec["total_cost_usd"] = safe_float(rec.get("total_cost_usd"), 0.0)
    rec["total_qty"] = safe_float(rec.get("total_qty"), 0.0)
    cb[symbol] = rec
    state["cost_basis"] = cb
    return rec

def cb_avg_entry(state: dict, symbol: str) -> float:
    rec = _cb_get(state, symbol)
    if rec["total_qty"] <= 0:
        return 0.0
    return rec["total_cost_usd"] / rec["total_qty"]

def cb_set_from_avg(state: dict, symbol: str, qty: float, avg_entry: float):
    qty = max(0.0, float(qty))
    avg_entry = max(0.0, float(avg_entry))
    cb = state.get("cost_basis", {})
    if not isinstance(cb, dict):
        cb = {}
    if qty <= 0 or avg_entry <= 0:
        cb[symbol] = {"total_cost_usd": 0.0, "total_qty": 0.0}
    else:
        cb[symbol] = {"total_cost_usd": qty * avg_entry, "total_qty": qty}
    state["cost_basis"] = cb

def cb_add_buy(state: dict, symbol: str, qty: float, price: float):
    qty = max(0.0, float(qty))
    price = max(0.0, float(price))
    rec = _cb_get(state, symbol)
    rec["total_cost_usd"] += qty * price
    rec["total_qty"] += qty
    state["cost_basis"][symbol] = rec

def cb_clear(state: dict, symbol: str):
    cb = state.get("cost_basis", {})
    if not isinstance(cb, dict):
        cb = {}
    cb[symbol] = {"total_cost_usd": 0.0, "total_qty": 0.0}
    state["cost_basis"] = cb

def breakeven_price(ctrl: dict, state: dict, symbol: str) -> float:
    avg = cb_avg_entry(state, symbol)
    if avg <= 0:
        return 0.0
    # conservative: require clearing estimated round-trip platform costs (not multiplier)
    cost_pct = platform_cost_pct(ctrl)
    return avg * (1.0 + cost_pct)
'''.lstrip("\n")

src = src[:anchor] + helpers + "\n" + src[anchor:]

# 3) Replace paper_buy to update cost basis
src = re.sub(
    r'def paper_buy\(state: dict, ctrl: dict, symbol: str, price: float\) -> dict:[\s\S]*?return \{"ok": True, "spent": spend, "qty": qty\}',
    r'''def paper_buy(state: dict, ctrl: dict, symbol: str, price: float) -> dict:
    cash = safe_float(state.get("cash_usd"), 0.0)
    min_order = float(PLATFORM_PROFILES.get(ctrl.get("platform","PAPER").upper(), PLATFORM_PROFILES["PAPER"]).get("min_order_usd", 5.0))
    pct = safe_float(ctrl.get("strategy", {}).get("max_position_pct", 0.35), 0.35)
    spend = cash * pct
    if spend < min_order:
        return {"ok": False, "reason": f"Spend ${spend:.2f} below min order ${min_order:.2f}"}
    qty = spend / price if price > 0 else 0.0
    if qty <= 0:
        return {"ok": False, "reason": "Invalid price/qty."}

    state["cash_usd"] = cash - spend
    set_holding(state, symbol, get_holding(state, symbol) + qty)

    # cost basis: add this buy
    cb_add_buy(state, symbol, qty, price)

    # position still tracked for convenience/UI, but PnL uses cost basis
    state["position"] = {"symbol": symbol, "entry_price": price, "qty": qty, "entry_ts": now_ts()}
    return {"ok": True, "spent": spend, "qty": qty}''',
    src,
    count=1
)

# 4) Replace paper_sell to compute pnl vs avg entry and clear cost basis
src = re.sub(
    r'def paper_sell\(state: dict, symbol: str, price: float\) -> dict:[\s\S]*?return \{"ok": True, "qty": qty, "proceeds": proceeds, "pnl": pnl\}',
    r'''def paper_sell(state: dict, symbol: str, price: float) -> dict:
    qty = get_holding(state, symbol)
    if qty <= 0:
        return {"ok": False, "reason": "No holdings to sell."}

    avg = cb_avg_entry(state, symbol)
    proceeds = qty * price
    state["cash_usd"] = safe_float(state.get("cash_usd"), 0.0) + proceeds

    # clear holdings + position + cost basis
    set_holding(state, symbol, 0.0)
    state["position"] = None
    cb_clear(state, symbol)

    pnl = (price - avg) * qty if avg > 0 else 0.0
    st = state.get("stats", {})
    st["pnl_usd"] = safe_float(st.get("pnl_usd"), 0.0) + pnl
    if avg > 0:
        if pnl >= 0:
            st["wins"] = int(st.get("wins", 0)) + 1
        else:
            st["losses"] = int(st.get("losses", 0)) + 1
    state["stats"] = st

    return {"ok": True, "qty": qty, "proceeds": proceeds, "pnl": pnl, "avg_entry": avg}''',
    src,
    count=1
)

# 5) Add a SELL cost-basis prompt inside prompt_confirm (only when missing)
# We'll inject just after holdings are computed.
inject_point = r'holdings = safe_float\(\(state.get\("holdings", \{\}\) or \{\}\)\.get\(symbol, 0\.0\), 0\.0\) if isinstance\(state, dict\) else 0\.0'
m = re.search(inject_point, src)
if not m:
    raise SystemExit("Patch failed: could not locate holdings line in prompt_confirm")

extra = r'''
    # If user already has holdings but no cost basis yet, prompt once (SELL only)
    avg_entry = cb_avg_entry(state, symbol) if isinstance(state, dict) else 0.0
    if action == "SELL" and holdings > 0 and avg_entry <= 0:
        try:
            info("Cost basis missing for current holdings.")
            ans = input("Enter your average buy price in USD (or blank to skip): ").strip()
            if ans:
                user_avg = safe_float(ans, 0.0)
                if user_avg > 0:
                    cb_set_from_avg(state, symbol, holdings, user_avg)
                    avg_entry = user_avg
                    info(f"Cost basis set: Avg Entry ${user_avg:.2f} for {holdings:.8f} BTC")
        except Exception:
            pass

    # Break-even + projected PnL context (SELL only, if avg_entry known)
    be = breakeven_price(ctrl, state, symbol) if (action == "SELL" and avg_entry > 0) else 0.0
    proj_pnl = ((price - avg_entry) * holdings) if (action == "SELL" and avg_entry > 0) else 0.0

    # Profit Favorability score (0-100). Not a promise — just context.
    favor = None
    if action == "SELL" and avg_entry > 0:
        # components: margin above break-even, RSI position, and fee-gate clearance
        margin = 0.0
        if be > 0:
            margin = (price - be) / be  # e.g., 0.02 = 2% above BE
        # normalize: margin contributes up to 60 pts
        m_pts = max(0.0, min(60.0, margin * 1200.0))  # 0.05 -> 60 pts
        # RSI contributes up to 25 pts (higher RSI => more sell-favorable)
        r_pts = max(0.0, min(25.0, (rsi - 50.0) * 0.5))  # rsi 100 -> 25
        # fee gate contributes up to 15 pts
        gate_pts = 15.0 if expected_move >= required_move else 0.0
        favor = int(max(0.0, min(100.0, m_pts + r_pts + gate_pts)))
'''.rstrip() + "\n"

# Insert extra right after the holdings line
start = m.end()
src = src[:start] + extra + src[start:]

# 6) Enhance SELL message to include cost basis context when available
# Replace the SELL msg block by adding lines.
src = re.sub(
    r'f"Suggested SELL: \{suggested_sell_btc:\.8f\} \{symbol\.split\(\'-\'\)\[0\]\} \(~\$\{suggested_sell_usd:\.2f\} after est costs\)\\n"\s*'
    r'f"Confirm within \{countdown\}s\? \(y/N\)"',
    r'f"Suggested SELL: {suggested_sell_btc:.8f} {symbol.split(\'-\')[0]} (~${suggested_sell_usd:.2f} after est costs)\\n"'
    r'                        + (f"Avg Entry: ${avg_entry:.2f} | Break-even: ${be:.2f} | Proj PnL: ${proj_pnl:.2f} | Favor: {favor}/100\\n" if (action=="SELL" and avg_entry>0) else "")'
    r'                        + f"Confirm within {countdown}s? (y/N)"',
    src,
    count=1
)

with open(PATH, "w", encoding="utf-8") as f:
    f.write(src)

print("v70 patch applied to", PATH)
