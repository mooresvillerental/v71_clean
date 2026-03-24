#!/usr/bin/env python3
from pathlib import Path
import re

P = Path("bin/backtest_90d_v1.py")
src = P.read_text(encoding="utf-8")

# ----------------------------
# Helpers
# ----------------------------
def insert_before(pattern, insert_text, text, flags=0, label=""):
    m = re.search(pattern, text, flags)
    if not m:
        print(f"[FAIL] {label} (anchor not found)")
        return text, False
    i = m.start()
    return text[:i] + insert_text + text[i:], True

def insert_after(pattern, insert_text, text, flags=0, label=""):
    m = re.search(pattern, text, flags)
    if not m:
        print(f"[FAIL] {label} (anchor not found)")
        return text, False
    i = m.end()
    return text[:i] + insert_text + text[i:], True

changed = False

# ----------------------------
# 1) Ensure imports exist
# (you already have these; we just avoid duplicates)
# ----------------------------
need_import = "from bin.regime_engine_v1 import RegimeConfig, build_regime_series, regime_multiplier, range_rsi_buy_threshold\n"
if need_import not in src:
    # Insert after other imports (before first def/class)
    src, ok = insert_before(r"(?m)^(def|class)\s", need_import, src, flags=0, label="Insert regime imports")
    changed = changed or ok
else:
    print("[OK] imports already present")

# ----------------------------
# 2) Add CLI args BEFORE parse_args (works whether args var is args or _a)
# ----------------------------
if "--regime-mode" not in src:
    args_snippet = """
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
    # Insert immediately before *any* parse_args assignment (args=... or _a=...)
    src, ok = insert_before(r"(?m)^[ \t]*\w+\s*=\s*parser\.parse_args\(\)\s*$", args_snippet, src, flags=0, label="Insert regime CLI args")
    changed = changed or ok
else:
    print("[OK] regime CLI args already present")

# ----------------------------
# 3) Create regime_cfg AFTER parse_args assignment (supports args or _a)
# ----------------------------
if "regime_cfg = RegimeConfig(" not in src:
    # detect args variable name
    m = re.search(r"(?m)^(?P<avar>\w+)\s*=\s*parser\.parse_args\(\)\s*$", src)
    if not m:
        print("[FAIL] could not find parser.parse_args() line for regime_cfg insertion")
    else:
        avar = m.group("avar")
        cfg_block = f"""

    # Regime config (stdlib-only)
    regime_cfg = RegimeConfig(
        enabled=bool(getattr({avar}, "regime_mode", False)),
        timeframe=str(getattr({avar}, "regime_tf", "1H")),
        ema_len=int(getattr({avar}, "regime_ema_len", 200)),
        slope_len=int(getattr({avar}, "regime_slope_len", 12)),
        buffer_pct=float(getattr({avar}, "regime_buffer_pct", 0.006)),
        confirm_bars=int(getattr({avar}, "regime_confirm_bars", 2)),
        bull_mult=float(getattr({avar}, "regime_bull_mult", 1.00)),
        range_mult=float(getattr({avar}, "regime_range_mult", 0.50)),
        bear_mult=float(getattr({avar}, "regime_bear_mult", 0.00)),
        range_rsi_buy_offset=float(getattr({avar}, "regime_range_rsi_buy_offset", 4.0)),
    )
"""
        # insert right after that parse_args line
        src, ok = insert_after(re.escape(m.group(0)), cfg_block, src, flags=0, label="Insert regime_cfg after parse_args")
        changed = changed or ok
else:
    print("[OK] regime_cfg already present")

# ----------------------------
# 4) Remove the wrongly inserted guards inside the signal-building loop
# We remove everything between:
#   if side=="BUY":
# and before:
#   elif side=="SELL":
# and replace with just conf calc placeholder.
# ----------------------------
# This is surgical: replace the whole BUY block content with a single conf line.
pattern_buy_block = re.compile(
    r'(?ms)(^\s*if\s+side=="BUY"\s*:\s*\n)(.*?)(^\s*elif\s+side=="SELL"\s*:\s*\n)',
)
m = pattern_buy_block.search(src)
if m:
    indent = re.match(r"^\s*", m.group(1)).group(0)
    replacement_mid = f"{indent}    conf = max(0.0, float(rsi_buy) - rsi)   # deeper oversold => higher\n"
    src2 = src[:m.start()] + m.group(1) + replacement_mid + m.group(3) + src[m.end():]
    if src2 != src:
        src = src2
        print("[OK] removed misplaced regime guards from event-builder BUY block")
        changed = True
else:
    print("[WARN] could not locate event-builder BUY/SELL conf block (may have different format)")

# ----------------------------
# 5) Build regime series per symbol after times/closes are fetched.
# We store reg_by_time in data[sym].
# Anchor: right after fetch_ohlc returns times, closes (line ~317 in your snippet).
# ----------------------------
if '"reg_by_time"' not in src:
    anchor = r"(?m)^\s*times,\s*closes\s*=\s*fetch_ohlc\([^\n]+\)\s*$"
    block = """
          # regime lookup per timestamp (aligned to candles)
          reg_by_time = None
          if 'regime_cfg' in locals() and regime_cfg.enabled:
              try:
                  candles = [{"ts": t, "close": c} for (t, c) in zip(times, closes)]
                  regs = build_regime_series(candles, regime_cfg)
                  reg_by_time = {times[i]: regs[i] for i in range(min(len(times), len(regs)))}
              except Exception as e:
                  print(f"WARN regime build failed for {sym}: {e}")
                  reg_by_time = None
"""
    src, ok = insert_after(anchor, block, src, flags=re.M, label="Insert reg_by_time build after fetch_ohlc")
    changed = changed or ok
else:
    print("[OK] reg_by_time already present")

# ----------------------------
# 6) Save reg_by_time into data[sym] dict
# Anchor: data[sym] = { ... }
# ----------------------------
# Replace the existing assignment line to include reg_by_time
src2 = re.sub(
    r'(?m)^\s*data\[sym\]\s*=\s*\{"times":\s*times,\s*"closes":\s*closes,\s*"sigs":\s*sigs\}\s*$',
    '          data[sym] = {"times": times, "closes": closes, "sigs": sigs, "reg_by_time": reg_by_time}',
    src
)
if src2 != src:
    src = src2
    print("[OK] added reg_by_time into data[sym]")
    changed = True
else:
    print("[WARN] could not patch data[sym] assignment to include reg_by_time (format mismatch)")

# ----------------------------
# 7) Add regime into events tuple
# events comment + append tuple
# ----------------------------
# Update events comment (optional)
src2 = re.sub(
    r'(?m)^\s*events\s*=\s*\[\]\s*#\s*\(t,\s*sym,\s*side,\s*price,\s*rsi,\s*confidence\)\s*$',
    '      events = []  # (t, sym, side, price, rsi, confidence, regime)',
    src
)
if src2 != src:
    src = src2
    print("[OK] updated events tuple comment")
    changed = True

# Patch events.append to include regime derived from reg_by_time
if "reg_by_time" in src and "events.append((t, sym, side, price, rsi, conf, regime))" not in src:
    # Insert regime lookup right before append inside the loop building events
    # Anchor on the append line in your snippet.
    src, ok = insert_before(
        r"(?m)^\s*events\.append\(\(t,\s*sym,\s*side,\s*price,\s*rsi,\s*conf\)\)\s*$",
        '              regime = (d.get("reg_by_time") or {}).get(t, "bull")\n',
        src,
        flags=0,
        label="Insert regime lookup before events.append"
    )
    changed = changed or ok

    src2 = re.sub(
        r"(?m)^\s*events\.append\(\(t,\s*sym,\s*side,\s*price,\s*rsi,\s*conf\)\)\s*$",
        "              events.append((t, sym, side, price, rsi, conf, regime))",
        src
    )
    if src2 != src:
        src = src2
        print("[OK] appended regime into events tuple")
        changed = True
    else:
        print("[WARN] could not patch events.append tuple (format mismatch)")
else:
    print("[OK] events already include regime or reg_by_time missing")

# ----------------------------
# 8) Update the execution loop unpacking and apply regime logic + sizing multiplier
# Anchor: for (t, sym, side, price, rsi, conf) in events:
# ----------------------------
src2 = re.sub(
    r"(?m)^\s*for\s+\(t,\s*sym,\s*side,\s*price,\s*rsi,\s*conf\)\s+in\s+events\s*:\s*$",
    "      for (t, sym, side, price, rsi, conf, regime) in events:",
    src
)
if src2 != src:
    src = src2
    print("[OK] updated execution loop to unpack regime")
    changed = True
else:
    print("[WARN] could not find execution loop unpacking line (format mismatch)")

# Insert reg_mult computation near top of execution loop (right after dd_now_pct calc is fine, but we can do early)
# We'll insert after dd_now_pct line.
if "reg_mult = " not in src:
    src, ok = insert_after(
        r"(?m)^\s*dd_now_pct\s*=\s*max\(0\.0,\s*\(_peak\s*-\s*_eq_now\)\s*/\s*_peak\)\s*\*\s*100\.0\s*$",
        "\n          # Regime multiplier for this event\n          reg_mult = regime_multiplier(regime, regime_cfg) if 'regime_cfg' in locals() else 1.0\n",
        src,
        flags=re.M,
        label="Insert reg_mult after dd_now_pct"
    )
    changed = changed or ok
else:
    print("[OK] reg_mult already present")

# Apply bear/range enforcement in the BUY execution path (correct place)
# Anchor: if pos_sym is None: then if side != "BUY": continue
# Insert AFTER side != "BUY" check and before selecting best signal.
if "Regime enforcement (BUY exec)" not in src:
    enforcement = """
              # Regime enforcement (BUY exec)
              if 'regime_cfg' in locals() and regime_cfg.enabled:
                  if regime == "bear":
                      continue
                  if regime == "range":
                      _range_thr = range_rsi_buy_threshold(float(rsi_buy), regime_cfg)
                      if float(rsi) > _range_thr:
                          continue
"""
    src, ok = insert_after(
        r"(?m)^\s*if\s+side\s*!=\s*\"BUY\"\s*:\s*\n\s*continue\s*$",
        enforcement,
        src,
        flags=re.M,
        label="Insert BUY exec regime enforcement"
    )
    changed = changed or ok
else:
    print("[OK] BUY exec regime enforcement already present")

# Multiply sizing by reg_mult (the correct line is: usd = max(... cash*trade_pct*mult))
# Replace that exact line to include reg_mult.
src2 = re.sub(
    r"(?m)^\s*usd\s*=\s*max\(\s*MIN_TRADE_USD\s*,\s*cash\*trade_pct\*mult\s*\)\s*$",
    "              usd = max(MIN_TRADE_USD, cash*trade_pct*mult*reg_mult)",
    src
)
if src2 != src:
    src = src2
    print("[OK] applied reg_mult to sizing usd calculation")
    changed = True
else:
    print("[WARN] could not patch usd sizing line (format mismatch)")

# ----------------------------
# Write file
# ----------------------------
P.write_text(src, encoding="utf-8")
print("\nDone. File updated." + (" (changed)" if changed else " (no changes?)"))
