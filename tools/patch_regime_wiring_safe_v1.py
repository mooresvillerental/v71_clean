#!/usr/bin/env python3
from pathlib import Path
import re

P = Path("bin/backtest_90d_v1.py")
src = P.read_text(encoding="utf-8")

def find1(pattern, flags=0):
    m = re.search(pattern, src, flags)
    return m

def insert_after_match(m, text):
    global src
    i = m.end()
    src = src[:i] + text + src[i:]

def insert_before_match(m, text):
    global src
    i = m.start()
    src = src[:i] + text + src[i:]

def ensure_once(needle, action_desc, fn):
    global src
    if needle in src:
        print(f"[SKIP] {action_desc} (already present)")
        return True
    ok = fn()
    print(("[OK]   " if ok else "[FAIL] ") + action_desc)
    return ok

ok_all = True

# 1) Imports (after existing imports, before first def/class)
IMPORT_LINE = "from bin.regime_engine_v1 import RegimeConfig, build_regime_series, regime_multiplier, range_rsi_buy_threshold\n"
def add_import():
    m = find1(r"(?m)^(def|class)\s")
    if not m:
        return False
    insert_before_match(m, IMPORT_LINE)
    return True
ok_all &= ensure_once("from bin.regime_engine_v1 import RegimeConfig", "Add regime_engine imports", add_import)

# 2) CLI args: insert before parse_args line (works regardless of args var name)
CLI_SNIP = """
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
def add_cli():
    m = find1(r"(?m)^(?P<indent>[ \t]*)\w+\s*=\s*parser\.parse_args\(\)\s*$")
    if not m:
        return False
    indent = m.group("indent")
    # Ensure snippet indentation matches surrounding code (same indent level as other parser.add_argument)
    text = "".join(indent + line + "\n" if line.strip() else "\n" for line in CLI_SNIP.strip("\n").splitlines())
    insert_before_match(m, text)
    return True
ok_all &= ensure_once("--regime-mode", "Add regime CLI args", add_cli)

# 3) regime_cfg after parse_args (detect args var name)
def add_regime_cfg():
    m = find1(r"(?m)^(?P<indent>[ \t]*)(?P<avar>\w+)\s*=\s*parser\.parse_args\(\)\s*$")
    if not m:
        return False
    indent = m.group("indent")
    avar = m.group("avar")
    cfg = f"""

{indent}# Regime config (stdlib-only)
{indent}regime_cfg = RegimeConfig(
{indent}    enabled=bool(getattr({avar}, "regime_mode", False)),
{indent}    timeframe=str(getattr({avar}, "regime_tf", "1H")),
{indent}    ema_len=int(getattr({avar}, "regime_ema_len", 200)),
{indent}    slope_len=int(getattr({avar}, "regime_slope_len", 12)),
{indent}    buffer_pct=float(getattr({avar}, "regime_buffer_pct", 0.006)),
{indent}    confirm_bars=int(getattr({avar}, "regime_confirm_bars", 2)),
{indent}    bull_mult=float(getattr({avar}, "regime_bull_mult", 1.00)),
{indent}    range_mult=float(getattr({avar}, "regime_range_mult", 0.50)),
{indent}    bear_mult=float(getattr({avar}, "regime_bear_mult", 0.00)),
{indent}    range_rsi_buy_offset=float(getattr({avar}, "regime_range_rsi_buy_offset", 4.0)),
{indent})
"""
    insert_after_match(m, cfg)
    return True
ok_all &= ensure_once("regime_cfg = RegimeConfig(", "Add regime_cfg init after parse_args()", add_regime_cfg)

# 4) Build reg_by_time after fetch_ohlc(...) line inside symbol loop
def add_reg_by_time():
    m = find1(r"(?m)^(?P<indent>[ \t]*)times,\s*closes\s*=\s*fetch_ohlc\([^\n]+\)\s*$")
    if not m:
        return False
    indent = m.group("indent")
    block = f"""

{indent}# regime lookup per timestamp (aligned to candles)
{indent}reg_by_time = None
{indent}if regime_cfg.enabled:
{indent}    try:
{indent}        _candles = [{{"ts": t, "close": c}} for (t, c) in zip(times, closes)]
{indent}        _regs = build_regime_series(_candles, regime_cfg)
{indent}        reg_by_time = {{times[i]: _regs[i] for i in range(min(len(times), len(_regs)))}}
{indent}    except Exception as e:
{indent}        print(f"WARN regime build failed for {{sym}}: {{e}}")
{indent}        reg_by_time = None
"""
    insert_after_match(m, block)
    return True
ok_all &= ensure_once("reg_by_time = None", "Build reg_by_time per symbol after fetch_ohlc()", add_reg_by_time)

# 5) Include reg_by_time in data[sym] assignment
def patch_data_assignment():
    global src
    pat = r'(?m)^(?P<indent>[ \t]*)data\[sym\]\s*=\s*\{"times":\s*times,\s*"closes":\s*closes,\s*"sigs":\s*sigs\}\s*$'
    m = re.search(pat, src)
    if not m:
        return False
    indent = m.group("indent")
    repl = f'{indent}data[sym] = {{"times": times, "closes": closes, "sigs": sigs, "reg_by_time": reg_by_time}}'
    src = re.sub(pat, repl, src)
    return True
ok_all &= ensure_once('"reg_by_time": reg_by_time', "Attach reg_by_time into data[sym]", patch_data_assignment)

# 6) Update events tuple: add regime
def patch_events_comment():
    global src
    src2 = re.sub(
        r'(?m)^(?P<indent>[ \t]*)events\s*=\s*\[\]\s*#\s*\(t,\s*sym,\s*side,\s*price,\s*rsi,\s*confidence\)\s*$',
        r'\g<indent>events = []  # (t, sym, side, price, rsi, confidence, regime)',
        src
    )
    if src2 == src:
        return False
    src = src2
    return True
ensure_once("confidence, regime", "Update events tuple comment", patch_events_comment)

def patch_events_append():
    global src
    # Insert regime = ... right before events.append(...)
    # Pattern match the append line
    pat_append = r'(?m)^(?P<indent>[ \t]*)events\.append\(\(t,\s*sym,\s*side,\s*price,\s*rsi,\s*conf\)\)\s*$'
    m = re.search(pat_append, src)
    if not m:
        return False
    indent = m.group("indent")
    ins = f'{indent}regime = (d.get("reg_by_time") or {{}}).get(t, "bull")\n'
    # Only insert once
    if "regime = (d.get(\"reg_by_time\")" in src:
        return True
    insert_before_match(m, ins)
    # Replace append tuple
    src = re.sub(pat_append, r'\g<indent>events.append((t, sym, side, price, rsi, conf, regime))', src)
    return True
ok_all &= ensure_once("events.append((t, sym, side, price, rsi, conf, regime))", "Attach regime into events.append()", patch_events_append)

# 7) Patch execution loop to unpack regime
def patch_exec_loop_unpack():
    global src
    src2 = re.sub(
        r"(?m)^(?P<indent>[ \t]*)for\s+\(t,\s*sym,\s*side,\s*price,\s*rsi,\s*conf\)\s+in\s+events\s*:\s*$",
        r"\g<indent>for (t, sym, side, price, rsi, conf, regime) in events:",
        src
    )
    if src2 == src:
        return False
    src = src2
    return True
ok_all &= ensure_once("conf, regime) in events", "Unpack regime in execution loop", patch_exec_loop_unpack)

# 8) Add reg_mult after dd_now_pct calc (inside exec loop)
def add_reg_mult():
    m = find1(r"(?m)^(?P<indent>[ \t]*)dd_now_pct\s*=\s*max\(0\.0,\s*\(_peak\s*-\s*_eq_now\)\s*/\s*_peak\)\s*\*\s*100\.0\s*$")
    if not m:
        return False
    indent = m.group("indent")
    block = f"\n{indent}# Regime multiplier for this event\n{indent}reg_mult = regime_multiplier(regime, regime_cfg) if regime_cfg.enabled else 1.0\n"
    insert_after_match(m, block)
    return True
ok_all &= ensure_once("reg_mult = regime_multiplier", "Compute reg_mult inside execution loop", add_reg_mult)

# 9) BUY exec enforcement: after `if side != "BUY": continue` in pos_sym is None block
def add_buy_exec_enforcement():
    m = find1(r"(?m)^(?P<indent>[ \t]*)if\s+side\s*!=\s*\"BUY\"\s*:\s*\n(?P=indent)\s*continue\s*$")
    if not m:
        return False
    indent = m.group("indent")
    inner = indent  # we insert at same block indent level as the surrounding code
    block = f"""

{inner}# Regime enforcement (BUY exec)
{inner}if regime_cfg.enabled:
{inner}    if regime == "bear":
{inner}        continue
{inner}    if regime == "range":
{inner}        _range_thr = range_rsi_buy_threshold(float(rsi_buy), regime_cfg)
{inner}        if float(rsi) > _range_thr:
{inner}            continue
"""
    insert_after_match(m, block)
    return True
ok_all &= ensure_once("Regime enforcement (BUY exec)", "Enforce bear/range rules in BUY execution path", add_buy_exec_enforcement)

# 10) Apply reg_mult to sizing line
def patch_usd_sizing():
    global src
    src2 = re.sub(
        r"(?m)^(?P<indent>[ \t]*)usd\s*=\s*max\(\s*MIN_TRADE_USD\s*,\s*cash\*trade_pct\*mult\s*\)\s*$",
        r"\g<indent>usd = max(MIN_TRADE_USD, cash*trade_pct*mult*reg_mult)",
        src
    )
    if src2 == src:
        return False
    src = src2
    return True
ok_all &= ensure_once("cash*trade_pct*mult*reg_mult", "Apply reg_mult to USD sizing", patch_usd_sizing)

P.write_text(src, encoding="utf-8")
print("\nPatch complete.")
if not ok_all:
    raise SystemExit(2)
