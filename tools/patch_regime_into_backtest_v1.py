#!/usr/bin/env python3
import re
from pathlib import Path

TARGET = Path("bin/backtest_90d_v1.py")
if not TARGET.exists():
    raise SystemExit(f"Missing: {TARGET}")

src = TARGET.read_text(encoding="utf-8")

def must_do(label, new_src, changed):
    if not changed:
        print(f"[FAIL] {label}: pattern not found / no change made")
        return new_src, False
    print(f"[OK]   {label}")
    return new_src, True

ok_all = True

# 1) Import regime engine (insert after risk engine import if found, else after other imports)
import_block = (
    "from bin.regime_engine_v1 import RegimeConfig, build_regime_series, "
    "regime_multiplier, range_rsi_buy_threshold\n"
)

if import_block not in src:
    # Prefer insert after risk_engine import
    m = re.search(r"(from\s+bin\.risk_engine_v1\s+import[^\n]*\n)", src)
    if m:
        insert_at = m.end(1)
        src = src[:insert_at] + import_block + src[insert_at:]
        print("[OK]   Added regime imports after risk_engine_v1 import")
    else:
        # Fallback: after last top-level import
        m2 = re.search(r"(\n)(?=(?:def|class)\s)", src)
        if m2:
            insert_at = m2.start(1) + 1
            src = src[:insert_at] + import_block + src[insert_at:]
            print("[OK]   Added regime imports after import section (fallback)")
        else:
            print("[FAIL] Could not place imports safely")
            ok_all = False
else:
    print("[SKIP] Regime imports already present")

# 2) Add CLI args (insert after --trade-pct if possible; else after parser creation)
args_snippet = r"""
    # --- Regime Detection v1 (OFF by default; stdlib-only) ---
    parser.add_argument("--regime-mode", action="store_true", help="Enable regime detection (bull/bear/range)")
    parser.add_argument("--regime-tf", default="1H", help="Regime timeframe (stdlib mode supports 1H)")
    parser.add_argument("--regime-ema-len", type=int, default=200, help="EMA length on regime timeframe")
    parser.add_argument("--regime-slope-len", type=int, default=12, help="EMA slope lookback on regime timeframe bars")
    parser.add_argument("--regime-buffer-pct", type=float, default=0.006, help="Hysteresis buffer around EMA (e.g., 0.006=0.6%)")
    parser.add_argument("--regime-confirm-bars", type=int, default=2, help="Consecutive bars to confirm bull/bear")
    parser.add_argument("--regime-bull-mult", type=float, default=1.00, help="Sizing multiplier in bull regime")
    parser.add_argument("--regime-range-mult", type=float, default=0.50, help="Sizing multiplier in range regime")
    parser.add_argument("--regime-bear-mult", type=float, default=0.00, help="Sizing multiplier in bear regime (0 disables new buys)")
    parser.add_argument("--regime-range-rsi-buy-offset", type=float, default=4.0, help="Range RSI buy becomes (rsi_buy - offset)")
"""

if "--regime-mode" not in src:
    # Try to insert after trade-pct arg
    m = re.search(r"(parser\.add_argument\([^\n]*--trade-pct[^\n]*\)\s*\n)", src)
    if m:
        insert_at = m.end(1)
        src = src[:insert_at] + args_snippet + src[insert_at:]
        print("[OK]   Added regime CLI args after --trade-pct")
    else:
        # Fallback: insert after parser = argparse.ArgumentParser(...)
        m2 = re.search(r"(parser\s*=\s*argparse\.ArgumentParser\([^\n]*\)\s*\n)", src)
        if m2:
            insert_at = m2.end(1)
            src = src[:insert_at] + args_snippet + src[insert_at:]
            print("[OK]   Added regime CLI args after parser creation (fallback)")
        else:
            print("[FAIL] Could not insert CLI args (no known anchor)")
            ok_all = False
else:
    print("[SKIP] Regime CLI args already present")

# 3) Create RegimeConfig after args parsed (safe; no data needed yet)
if "RegimeConfig(" not in src:
    m = re.search(r"(args\s*=\s*parser\.parse_args\(\)\s*\n)", src)
    if m:
        insert_at = m.end(1)
        cfg_block = """
    # Regime config (stdlib-only). Regime series is built after candles are loaded.
    regime_cfg = RegimeConfig(
        enabled=bool(getattr(args, "regime_mode", False)),
        timeframe=str(getattr(args, "regime_tf", "1H")),
        ema_len=int(getattr(args, "regime_ema_len", 200)),
        slope_len=int(getattr(args, "regime_slope_len", 12)),
        buffer_pct=float(getattr(args, "regime_buffer_pct", 0.006)),
        confirm_bars=int(getattr(args, "regime_confirm_bars", 2)),
        bull_mult=float(getattr(args, "regime_bull_mult", 1.00)),
        range_mult=float(getattr(args, "regime_range_mult", 0.50)),
        bear_mult=float(getattr(args, "regime_bear_mult", 0.00)),
        range_rsi_buy_offset=float(getattr(args, "regime_range_rsi_buy_offset", 4.0)),
    )
    regimes = None  # built later after candles exist
"""
        src = src[:insert_at] + cfg_block + src[insert_at:]
        print("[OK]   Added regime_cfg init after parse_args()")
    else:
        print("[FAIL] Could not find args = parser.parse_args() anchor")
        ok_all = False
else:
    print("[SKIP] regime_cfg already present")

# 4) Build regimes after candles are loaded.
# We look for a first assignment to a variable named 'candles' (common in your codebase).
if "build_regime_series(" not in src:
    m = re.search(r"(^\s*candles\s*=\s*[^\n]+\n)", src, flags=re.M)
    if m:
        insert_at = m.end(1)
        block = """
    # Build per-candle regimes aligned to candles (forward-filled from 1H buckets)
    if regime_cfg.enabled:
        try:
            regimes = build_regime_series(candles, regime_cfg)
        except Exception as e:
            print(f"[WARN] Regime build failed; continuing with bull regime. err={e}")
            regimes = ["bull"] * len(candles)
    else:
        regimes = ["bull"] * len(candles)
"""
        src = src[:insert_at] + block + src[insert_at:]
        print("[OK]   Inserted build_regime_series(candles, regime_cfg) after candles=")
    else:
        print("[FAIL] Could not find a 'candles =' assignment to attach regime build.")
        ok_all = False
else:
    print("[SKIP] regime series build already present")

# 5) In the main event loop, compute regime + multiplier (very lightweight)
# Insert after a loop header like: for i, c in enumerate(candles):
if "regime = " not in src:
    m = re.search(r"(^\s*for\s+(\w+)\s*,\s*(\w+)\s+in\s+enumerate\(\s*candles\s*\)\s*:\s*\n)", src, flags=re.M)
    if m:
        insert_at = m.end(1)
        i_var, c_var = m.group(2), m.group(3)
        loop_block = f"""\
        # Regime for this candle (aligned 1:1)
        regime = regimes[{i_var}] if regimes and {i_var} < len(regimes) else "bull"
        reg_mult = regime_multiplier(regime, regime_cfg)
"""
        src = src[:insert_at] + loop_block + src[insert_at:]
        print("[OK]   Added per-candle regime/reg_mult inside loop")
    else:
        print("[FAIL] Could not find 'for i, c in enumerate(candles):' loop header")
        ok_all = False
else:
    print("[SKIP] per-candle regime assignment already present")

# 6) Apply bear/range behavior at BUY execution time (no changes to signal builder needed)
# We patch the BUY execution block by injecting guards immediately after detecting a BUY signal.
# Try common patterns: if signal == "BUY": or if side == "BUY":
if "Range RSI gate" not in src:
    injected = False
    patterns = [
        r"(^\s*if\s+signal\s*==\s*[\"']BUY[\"']\s*:\s*\n)",
        r"(^\s*if\s+side\s*==\s*[\"']BUY[\"']\s*:\s*\n)",
    ]
    for pat in patterns:
        m = re.search(pat, src, flags=re.M)
        if m:
            insert_at = m.end(1)
            guard = """
            # --- Regime guards (v1 conservative) ---
            # Bear: block new BUYs (long-only defense)
            if regime_cfg.enabled and regime == "bear":
                continue

            # Range: require stricter RSI buy threshold at execution time.
            # We try to use an in-scope variable named 'rsi' or 'rsi_now' if present.
            if regime_cfg.enabled and regime == "range":
                _base_rsi_buy = float(getattr(args, "rsi_buy", 42))
                _range_thr = range_rsi_buy_threshold(_base_rsi_buy, regime_cfg)
                _rsi_val = None
                if "rsi" in locals():
                    try: _rsi_val = float(rsi)
                    except Exception: _rsi_val = None
                if _rsi_val is None and "rsi_now" in locals():
                    try: _rsi_val = float(rsi_now)
                    except Exception: _rsi_val = None
                if _rsi_val is not None and _rsi_val > _range_thr:
                    continue
"""
            src = src[:insert_at] + guard + src[insert_at:]
            print("[OK]   Injected Bear/Range BUY guards inside BUY block")
            injected = True
            break
    if not injected:
        print("[FAIL] Could not find BUY execution block to inject guards")
        ok_all = False
else:
    print("[SKIP] BUY guards already present")

# 7) Apply sizing multiplier: multiply existing sizing by reg_mult
# Try to patch a line that computes USD spend using trade_pct and a size multiplier.
# We do a conservative replacement: whenever we see "* trade_pct" and "* size_mult" in same line, append "* reg_mult"
if "* reg_mult" not in src:
    replaced = 0
    lines = src.splitlines(True)
    out_lines = []
    for ln in lines:
        if ("trade_pct" in ln and ("size_mult" in ln or "risk_mult" in ln) and "reg_mult" not in ln
            and ("=" in ln) and ("equity" in ln or "cash" in ln)):
            # Append reg_mult at end of RHS if it looks multiplicative
            if re.search(r"=\s*.*\*\s*(size_mult|risk_mult)\b", ln):
                ln = ln.rstrip("\n") + " * reg_mult\n"
                replaced += 1
        out_lines.append(ln)
    src2 = "".join(out_lines)
    if replaced > 0:
        src = src2
        print(f"[OK]   Appended '* reg_mult' to {replaced} sizing line(s)")
    else:
        print("[WARN] Could not confidently find sizing line to multiply by reg_mult (manual follow-up may be needed)")
else:
    print("[SKIP] sizing already uses reg_mult")

TARGET.write_text(src, encoding="utf-8")
print("\nPatch complete.")
if not ok_all:
    print("Some anchors were not found. Paste the LAST ~30 lines of:")
    print("  python -m py_compile bin/backtest_90d_v1.py")
    raise SystemExit(2)
