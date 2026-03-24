#!/usr/bin/env python3
from pathlib import Path
import re

p = Path("bin/backtest_90d_v1.py")
src = p.read_text(encoding="utf-8")

if "--regime-mode" in src:
    print("[SKIP] Regime CLI args already present in file")
    raise SystemExit(0)

# Anchor on the parse_args line (works regardless of args var name)
m = re.search(r'(?m)^(?P<indent>[ \t]*)(?P<avar>\w+)\s*=\s*parser\.parse_args\(\)\s*$', src)
if not m:
    raise SystemExit("[FAIL] Could not find '<var> = parser.parse_args()' in backtest_90d_v1.py")

indent = m.group("indent")

block = f"""
{indent}# --- Regime Detection v1 (OFF by default; stdlib-only) ---
{indent}parser.add_argument("--regime-mode", action="store_true", help="Enable regime detection (bull/bear/range)")
{indent}parser.add_argument("--regime-tf", default="1H", help="Regime timeframe (stdlib mode supports 1H)")
{indent}parser.add_argument("--regime-ema-len", type=int, default=200, help="EMA length on regime timeframe")
{indent}parser.add_argument("--regime-slope-len", type=int, default=12, help="EMA slope lookback on regime timeframe bars")
{indent}parser.add_argument("--regime-buffer-pct", type=float, default=0.006, help="Hysteresis buffer around EMA (e.g., 0.006=0.6%)")
{indent}parser.add_argument("--regime-confirm-bars", type=int, default=2, help="Consecutive bars to confirm bull/bear")
{indent}parser.add_argument("--regime-bull-mult", type=float, default=1.00, help="Sizing multiplier in bull regime")
{indent}parser.add_argument("--regime-range-mult", type=float, default=0.50, help="Sizing multiplier in range regime")
{indent}parser.add_argument("--regime-bear-mult", type=float, default=0.00, help="Sizing multiplier in bear regime (0 disables new buys)")
{indent}parser.add_argument("--regime-range-rsi-buy-offset", type=float, default=4.0, help="Range RSI buy becomes (rsi_buy - offset)")
"""

src = src[:m.start()] + block + src[m.start():]
p.write_text(src, encoding="utf-8")
print("[OK] Inserted regime CLI args before parse_args()")
