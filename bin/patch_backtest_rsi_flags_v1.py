from pathlib import Path
import re, sys

p = Path("bin/backtest_90d_v1.py")
s = p.read_text("utf-8", errors="replace")

# 1) Replace the hardcoded build_signals call
#    sigs = build_signals(times, closes, 30.0, 70.0)
s2, n1 = re.subn(
    r'sigs\s*=\s*build_signals\(\s*times\s*,\s*closes\s*,\s*30\.0\s*,\s*70\.0\s*\)',
    'sigs = build_signals(times, closes, args.rsi_buy, args.rsi_sell)',
    s,
    count=1
)

if n1 != 1:
    print("PATCH FAILED: could not replace hardcoded build_signals(times, closes, 30.0, 70.0)")
    sys.exit(1)

# 2) Replace confidence lines to use args thresholds instead of 30/70
#    conf = max(0.0, 30.0 - rsi)
s2, n2 = re.subn(
    r'conf\s*=\s*max\(\s*0\.0\s*,\s*30\.0\s*-\s*rsi\s*\)',
    'conf = max(0.0, float(args.rsi_buy) - rsi)   # deeper oversold => higher',
    s2,
    count=1
)

#    conf = max(0.0, rsi - 70.0)
s2, n3 = re.subn(
    r'conf\s*=\s*max\(\s*0\.0\s*,\s*rsi\s*-\s*70\.0\s*\)',
    'conf = max(0.0, rsi - float(args.rsi_sell))  # more overbought => higher',
    s2,
    count=1
)

# n2/n3 might be 0 if your file evolved, but if so we still want to know.
# The hardcoded build_signals was the main functional issue.
p.write_text(s2, "utf-8")
print("OK ✅ Patched build_signals + confidence to use args.rsi_buy / args.rsi_sell")
print(f"replaced build_signals: {n1}  conf_lo: {n2}  conf_hi: {n3}")
