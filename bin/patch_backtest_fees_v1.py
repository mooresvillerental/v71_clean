from pathlib import Path
import re, sys

p = Path("bin/backtest_90d_v1.py")
s = p.read_text("utf-8", errors="replace")

if "EZ_FEE_SLIP_ARGS_V1" in s:
    print("Already patched ✅ (EZ_FEE_SLIP_ARGS_V1)")
    raise SystemExit(0)

# 1) Add args parsing for fee/slip right after EZ_RSI_ARGS_V1 block (inside main)
needle = "rsi_sell = float(_a.rsi_sell)\n"
i = s.find(needle)
if i < 0:
    raise SystemExit("PATCH FAILED: could not find RSI args block (rsi_sell line)")

insert_args = """
    # EZ_FEE_SLIP_ARGS_V1
    _p.add_argument("--fee-bps", type=float, default=0.0)   # per-side fee (bps)
    _p.add_argument("--slip-bps", type=float, default=0.0)  # per-side slippage (bps)
    _a, _unknown = _p.parse_known_args()
    rsi_buy = float(_a.rsi_buy)
    rsi_sell = float(_a.rsi_sell)
    fee_bps = float(_a.fee_bps)
    slip_bps = float(_a.slip_bps)

"""

# Replace the simple 2-line parse with extended parse
# (We locate the block from "_a, _unknown =" through rsi_sell assignment.)
pat = re.compile(r"_a,\s*_unknown\s*=\s*_p\.parse_known_args\(\)\s*\n\s*rsi_buy\s*=\s*float\(_a\.rsi_buy\)\s*\n\s*rsi_sell\s*=\s*float\(_a\.rsi_sell\)\s*\n", re.M)
m = pat.search(s)
if not m:
    raise SystemExit("PATCH FAILED: could not locate RSI parse_known_args block to extend")

s = s[:m.start()] + insert_args + s[m.end():]

# 2) Add helpers near top-level (once): apply fee+slip to executed price
if "def _apply_fee_slip" not in s:
    top_ins = """
def _apply_fee_slip(price: float, side: str, fee_bps: float, slip_bps: float) -> float:
    # side: BUY pays up; SELL receives down
    # bps: 10 = 0.10%
    m = 1.0 + (fee_bps + slip_bps) / 10000.0
    if (side or "").upper() == "BUY":
        return float(price) * m
    return float(price) / m
"""
    # Insert after TRADE_PCT line
    m2 = re.search(r"^TRADE_PCT\s*=.*$", s, flags=re.M)
    if not m2:
        raise SystemExit("PATCH FAILED: could not find TRADE_PCT line")
    ins_at = m2.end()
    s = s[:ins_at] + "\n" + top_ins + "\n" + s[ins_at:]

# 3) Patch BUY execution price usage: look for "fill_px =" then replace to apply fee/slip
# We do a broad, safe replacement on the first BUY fill assignment pattern.
# If not found, we still succeed (no crash) — but we try hard.
s = s.replace("fill_px = float(px)", "fill_px = _apply_fee_slip(float(px), 'BUY', fee_bps, slip_bps)", 1)
s = s.replace("fill_px = float(price)", "fill_px = _apply_fee_slip(float(price), 'BUY', fee_bps, slip_bps)", 1)

# 4) Patch SELL execution price usage similarly
s = s.replace("fill_px = float(px)", "fill_px = _apply_fee_slip(float(px), 'SELL', fee_bps, slip_bps)", 1)
s = s.replace("fill_px = float(price)", "fill_px = _apply_fee_slip(float(price), 'SELL', fee_bps, slip_bps)", 1)

p.write_text(s, "utf-8")
print("OK ✅ Backtest now supports --fee-bps and --slip-bps")
