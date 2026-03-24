from pathlib import Path
import re, sys

p = Path("bin/backtest_90d_v1.py")
s = p.read_text("utf-8", errors="replace")

# We want to replace args.rsi_buy/args.rsi_sell with an existing symbol.
# Prefer local-style names if present, else globals-style, else fallback.
if re.search(r'\brsi_buy\b', s) and re.search(r'\brsi_sell\b', s):
    buy_ref  = "rsi_buy"
    sell_ref = "rsi_sell"
elif re.search(r'\bRSI_BUY\b', s) and re.search(r'\bRSI_SELL\b', s):
    buy_ref  = "RSI_BUY"
    sell_ref = "RSI_SELL"
else:
    # last resort: don't crash; keep working
    buy_ref  = "30.0"
    sell_ref = "70.0"

s2 = s

# 1) build_signals call
s2, n1 = re.subn(
    r'sigs\s*=\s*build_signals\(\s*times\s*,\s*closes\s*,\s*args\.rsi_buy\s*,\s*args\.rsi_sell\s*\)',
    f'sigs = build_signals(times, closes, float({buy_ref}), float({sell_ref}))',
    s2,
    count=1
)

# 2) confidence lines (if present from our earlier patch)
s2 = s2.replace('float(args.rsi_buy)', f'float({buy_ref})')
s2 = s2.replace('float(args.rsi_sell)', f'float({sell_ref})')

p.write_text(s2, "utf-8")
print("OK ✅ Fixed NameError: args (now using:", buy_ref, "/", sell_ref, ")")
print("replaced build_signals call:", n1)
