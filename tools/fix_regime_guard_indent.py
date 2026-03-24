#!/usr/bin/env python3
import re
from pathlib import Path

p = Path("bin/backtest_90d_v1.py")
src = p.read_text(encoding="utf-8")

# 1) Remove any previously injected guard block (broken indentation)
guard_re = re.compile(
    r"\n[ \t]*# --- Regime guards \(v1 conservative\) ---.*?\n(?=\s*\n|\s*#|\s*(elif|else|if|for|while|return|continue|break)\b|\Z)",
    re.S
)

src2, n = guard_re.subn("\n", src)
if n:
    print(f"[OK] Removed {n} injected guard block(s)")
    src = src2
else:
    print("[WARN] No injected guard block found to remove (continuing)")

# 2) Find the BUY execution block line and capture its indentation
# We support a couple common patterns.
m = re.search(r"(?m)^(?P<indent>[ \t]*)if\s+(signal|side)\s*==\s*['\"]BUY['\"]\s*:\s*$", src)
if not m:
    raise SystemExit("[FAIL] Could not find a BUY block line like: if signal == 'BUY':")

buy_indent = m.group("indent")
inner = buy_indent + (" " * 4)  # standard 4-space block indent

guard_block = (
    f"{inner}# --- Regime guards (v1 conservative) ---\n"
    f"{inner}# Bear: block new BUYs (long-only defense)\n"
    f"{inner}if getattr(args, 'regime_mode', False) and (locals().get('regime') == 'bear'):\n"
    f"{inner}    continue\n\n"
    f"{inner}# Range: require stricter RSI buy threshold at execution time.\n"
    f"{inner}# Uses in-scope rsi/rsi_now if available; otherwise does nothing.\n"
    f"{inner}if getattr(args, 'regime_mode', False) and (locals().get('regime') == 'range'):\n"
    f"{inner}    _base_rsi_buy = float(getattr(args, 'rsi_buy', 42))\n"
    f"{inner}    _range_thr = range_rsi_buy_threshold(_base_rsi_buy, regime_cfg) if 'regime_cfg' in locals() else (_base_rsi_buy - 4.0)\n"
    f"{inner}    _rsi_val = None\n"
    f"{inner}    if 'rsi' in locals():\n"
    f"{inner}        try: _rsi_val = float(rsi)\n"
    f"{inner}        except Exception: _rsi_val = None\n"
    f"{inner}    if _rsi_val is None and 'rsi_now' in locals():\n"
    f"{inner}        try: _rsi_val = float(rsi_now)\n"
    f"{inner}        except Exception: _rsi_val = None\n"
    f"{inner}    if _rsi_val is not None and _rsi_val > _range_thr:\n"
    f"{inner}        continue\n"
)

# 3) Insert guard block immediately after the BUY line
insert_at = m.end(0)
src = src[:insert_at] + "\n" + guard_block + src[insert_at:]

p.write_text(src, encoding="utf-8")
print("[OK] Re-inserted guard block with correct indentation")
