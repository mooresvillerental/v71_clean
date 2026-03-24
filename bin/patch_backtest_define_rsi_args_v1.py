from pathlib import Path
import re, sys

p = Path("bin/backtest_90d_v1.py")
s = p.read_text("utf-8", errors="replace")

# If it's already patched, don't double insert
if "EZ_RSI_ARGS_V1" in s:
    print("Already patched ✅ (EZ_RSI_ARGS_V1)")
    raise SystemExit(0)

m = re.search(r'^\s*def\s+main\s*\(\s*\)\s*:\s*$', s, flags=re.M)
if not m:
    raise SystemExit("PATCH FAILED: could not find `def main():`")

# insert immediately after def main():
ins_at = m.end()

inject = """
    # EZ_RSI_ARGS_V1
    # Parse RSI thresholds from CLI (defaults match classic 30/70)
    import argparse
    _p = argparse.ArgumentParser(add_help=False)
    _p.add_argument("--rsi-buy", type=float, default=30.0)
    _p.add_argument("--rsi-sell", type=float, default=70.0)
    _a, _unknown = _p.parse_known_args()
    rsi_buy = float(_a.rsi_buy)
    rsi_sell = float(_a.rsi_sell)

"""

s2 = s[:ins_at] + inject + s[ins_at:]
p.write_text(s2, "utf-8")
print("OK ✅ Inserted RSI arg parsing inside main()")
