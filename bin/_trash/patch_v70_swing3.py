import re, sys

PATH = "v70_app_ready_pro.py"

with open(PATH, "r", encoding="utf-8") as f:
    s = f.read()

def die(msg):
    print(msg)
    sys.exit(1)

# ---------- 1) Add swing gate settings to DEFAULT_CTRL strategy ----------
# Add right after stop_loss_pct if not present.
if "swing_gate_pct" not in s:
    s2, n = re.subn(
        r'("stop_loss_pct"\s*:\s*0\.015\s*)',
        r'\1,\n        "swing_gate_pct": 0.03,  # require 3% dip/peak before BUY/SELL prompts\n        "swing_lookback": 60,   # number of recent price points used for swing calc\n',
        s,
        count=1
    )
    if n != 1:
        die("Patch failed: couldn't inject swing_gate_pct into DEFAULT_CTRL['strategy']")
    s = s2

# ---------- 2) Inject swing-gate calculations into decide_action ----------
# Insert right after holding_qty line.
anchor_pat = r'(holding_qty\s*=\s*get_holding\(state,\s*sample\.symbol\)\s*\n)'
m = re.search(anchor_pat, s)
if not m:
    die("Patch failed: couldn't find holding_qty line in decide_action()")

insert = r'''\1
    # -------------------------
    # SWING GATE (bigger dips/peaks)
    # BUY only if price is >= swing_gate% below recent high
    # SELL only if price is >= swing_gate% above recent low
    # STOP_LOSS bypasses this gate for safety.
    # -------------------------
    swing_gate = safe_float(strat.get("swing_gate_pct", 0.03), 0.03)
    lookback = int(safe_float(strat.get("swing_lookback", 60), 60))
    if lookback < 10:
        lookback = 10
    window = price_hist[-lookback:] if isinstance(price_hist, list) and price_hist else []
    if not window:
        window = [sample.price]
    recent_high = max(window) if window else sample.price
    recent_low  = min(window) if window else sample.price
    drop_from_high = ((recent_high - sample.price) / recent_high) if recent_high > 0 else 0.0
    rise_from_low  = ((sample.price - recent_low) / recent_low) if recent_low > 0 else 0.0
'''
s = re.sub(anchor_pat, insert, s, count=1)

# ---------- 3) Replace SELL RSI block to require 3% rise from recent low ----------
old_sell_rsi_pat = r'''
    # Sell logic: prioritize if holding
    if holding_qty > 0 and sample\.rsi >= rsi_sell:
        return "SELL", "RSI_SELL"
'''
if not re.search(old_sell_rsi_pat, s, flags=re.X):
    die("Patch failed: couldn't find the original RSI_SELL block to replace.")

new_sell_rsi = r'''
    # Sell logic: prioritize if holding
    if holding_qty > 0 and sample.rsi >= rsi_sell:
        if swing_gate <= 0 or rise_from_low >= swing_gate:
            return "SELL", "RSI_SELL"
        return None, "BLOCK_SWING_GATE_SELL"
'''
s = re.sub(old_sell_rsi_pat, new_sell_rsi, s, count=1, flags=re.X)

# ---------- 4) Replace TAKE_PROFIT block to require 3% rise; STOP_LOSS unchanged ----------
old_tp_sl_pat = r'''
            if gain >= tp:
                return "SELL", "TAKE_PROFIT"
            if gain <= -sl:
                return "SELL", "STOP_LOSS"
'''
if not re.search(old_tp_sl_pat, s, flags=re.X):
    die("Patch failed: couldn't find the original TAKE_PROFIT / STOP_LOSS block to replace.")

new_tp_sl = r'''
            if gain >= tp:
                if swing_gate <= 0 or rise_from_low >= swing_gate:
                    return "SELL", "TAKE_PROFIT"
                return None, "BLOCK_SWING_GATE_TP"
            if gain <= -sl:
                return "SELL", "STOP_LOSS"
'''
s = re.sub(old_tp_sl_pat, new_tp_sl, s, count=1, flags=re.X)

# ---------- 5) Replace BUY block to require 3% drop from recent high ----------
old_buy_pat = r'''
    # Buy logic: only if not holding
    if holding_qty <= 0 and sample\.rsi <= rsi_buy:
        return "BUY", "RSI_BUY"
'''
if not re.search(old_buy_pat, s, flags=re.X):
    die("Patch failed: couldn't find the original RSI_BUY block to replace.")

new_buy = r'''
    # Buy logic: only if not holding
    if holding_qty <= 0 and sample.rsi <= rsi_buy:
        if swing_gate <= 0 or drop_from_high >= swing_gate:
            return "BUY", "RSI_BUY"
        return None, "BLOCK_SWING_GATE_BUY"
'''
s = re.sub(old_buy_pat, new_buy, s, count=1, flags=re.X)

with open(PATH, "w", encoding="utf-8") as f:
    f.write(s)

print("OK: Applied 3% swing gate patch to", PATH)
