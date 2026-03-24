#!/usr/bin/env python3
from pathlib import Path
import re

p = Path("bin/backtest_90d_v1.py")
src = p.read_text(encoding="utf-8")

if "regime_cfg = RegimeConfig(" in src:
    print("[OK] regime_cfg already present in file (but may be in wrong scope). We'll ensure correct placement.")
# Remove any existing regime_cfg block to prevent duplicates in wrong scope
src = re.sub(r"(?ms)^\s*# Regime config \(stdlib-only\)\s*regime_cfg\s*=\s*RegimeConfig\(\s*.*?\)\s*$", "", src)

# 1) Preferred: insert after `_a = parser.parse_args()` (your code uses _a)
m = re.search(r"(?m)^(?P<indent>[ \t]*)_a\s*=\s*parser\.parse_args\(\)\s*$", src)
if m:
    indent = m.group("indent")
    block = f"""

{indent}# Regime config (stdlib-only) — must be defined before candle fetch loop
{indent}regime_cfg = RegimeConfig(
{indent}    enabled=bool(getattr(_a, "regime_mode", False)),
{indent}    timeframe=str(getattr(_a, "regime_tf", "1H")),
{indent}    ema_len=int(getattr(_a, "regime_ema_len", 200)),
{indent}    slope_len=int(getattr(_a, "regime_slope_len", 12)),
{indent}    buffer_pct=float(getattr(_a, "regime_buffer_pct", 0.006)),
{indent}    confirm_bars=int(getattr(_a, "regime_confirm_bars", 2)),
{indent}    bull_mult=float(getattr(_a, "regime_bull_mult", 1.00)),
{indent}    range_mult=float(getattr(_a, "regime_range_mult", 0.50)),
{indent}    bear_mult=float(getattr(_a, "regime_bear_mult", 0.00)),
{indent}    range_rsi_buy_offset=float(getattr(_a, "regime_range_rsi_buy_offset", 4.0)),
{indent})
"""
    insert_at = m.end()
    src = src[:insert_at] + block + src[insert_at:]
    print("[OK] Inserted regime_cfg after _a = parser.parse_args()")
else:
    # 2) Fallback: insert before risk_cfg = RiskConfig(
    m2 = re.search(r"(?m)^(?P<indent>[ \t]*)risk_cfg\s*=\s*RiskConfig\(\s*$", src)
    if not m2:
        raise SystemExit("[FAIL] Could not find _a=parse_args or risk_cfg=RiskConfig anchor")
    indent = m2.group("indent")
    block = f"""{indent}# Regime config (stdlib-only) — must be defined before candle fetch loop
{indent}regime_cfg = RegimeConfig(
{indent}    enabled=bool(getattr(_a, "regime_mode", False)) if '_a' in locals() else False,
{indent}    timeframe=str(getattr(_a, "regime_tf", "1H")) if '_a' in locals() else "1H",
{indent}    ema_len=int(getattr(_a, "regime_ema_len", 200)) if '_a' in locals() else 200,
{indent}    slope_len=int(getattr(_a, "regime_slope_len", 12)) if '_a' in locals() else 12,
{indent}    buffer_pct=float(getattr(_a, "regime_buffer_pct", 0.006)) if '_a' in locals() else 0.006,
{indent}    confirm_bars=int(getattr(_a, "regime_confirm_bars", 2)) if '_a' in locals() else 2,
{indent}    bull_mult=float(getattr(_a, "regime_bull_mult", 1.00)) if '_a' in locals() else 1.0,
{indent}    range_mult=float(getattr(_a, "regime_range_mult", 0.50)) if '_a' in locals() else 0.5,
{indent}    bear_mult=float(getattr(_a, "regime_bear_mult", 0.00)) if '_a' in locals() else 0.0,
{indent}    range_rsi_buy_offset=float(getattr(_a, "regime_range_rsi_buy_offset", 4.0)) if '_a' in locals() else 4.0,
{indent})
"""
    src = src[:m2.start()] + block + "\n" + src[m2.start():]
    print("[OK] Inserted regime_cfg before risk_cfg block (fallback)")

p.write_text(src, encoding="utf-8")
print("Done.")
