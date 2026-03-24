#!/usr/bin/env python3
from pathlib import Path
import re, time, sys

p = Path("bin/backtest_90d_v1.py")
s = p.read_text("utf-8", errors="replace")

bak = p.with_suffix(f".py.bak_{int(time.time())}")
bak.write_text(s, "utf-8")

# --- A) Ensure argparse flag exists (add if missing) ---
if "--confirm-turn" not in s and "confirm_turn" not in s:
    # Find argparse parser creation
    m = re.search(r"(parser\s*=\s*argparse\.ArgumentParser\([^\)]*\)\s*)", s)
    if not m:
        print("ERROR: Could not find argparse.ArgumentParser(...) in backtest file.")
        sys.exit(2)

    # Find a reasonable insertion point: after the last parser.add_argument(...) block (or right after parser=...)
    insert_at = None
    adds = list(re.finditer(r"^\s*parser\.add_argument\(", s, flags=re.M))
    insert_at = adds[-1].end() if adds else m.end()

    flag_block = r'''

# EZ_CONFIRM_TURN_V1
parser.add_argument("--confirm-turn", dest="confirm_turn", action="store_true",
                    help="Require 1-candle reversal confirmation: BUY only if price > prior event price; SELL only if price < prior event price.")
parser.add_argument("--no-confirm-turn", dest="confirm_turn", action="store_false",
                    help="Disable 1-candle reversal confirmation.")
parser.set_defaults(confirm_turn=True)
'''
    s = s[:insert_at] + flag_block + s[insert_at:]

# --- B) Inject turn confirmation into the per-symbol events loop ---
# We expect a loop line like:
#   for (t, side, price, rsi) in d["sigs"]:
loop_pat = re.compile(r'^\s*for\s*\(\s*t\s*,\s*side\s*,\s*price\s*,\s*rsi\s*\)\s*in\s*d\["sigs"\]\s*:\s*$', re.M)
m = loop_pat.search(s)
if not m:
    print('ERROR: Could not find loop: for (t, side, price, rsi) in d["sigs"]:')
    sys.exit(3)

# Add last_event_price initialization just before the loop (if not already there)
pre = s[:m.start()]
if "EZ_CONFIRM_TURN_V1_STATE" not in pre[-1200:]:
    pre = pre + "\n        # EZ_CONFIRM_TURN_V1_STATE\n        last_event_price = None\n"

# Insert checks immediately after the loop line (first statements inside loop)
# We'll keep indentation based on the loop line indentation.
loop_line = m.group(0)
indent = re.match(r'^(\s*)for', loop_line).group(1)
inner = indent + "    "

inject = (
    f"\n{inner}# EZ_CONFIRM_TURN_V1\n"
    f"{inner}if getattr(args, 'confirm_turn', True):\n"
    f"{inner}    if last_event_price is not None:\n"
    f"{inner}        if side == 'BUY' and not (price > last_event_price):\n"
    f"{inner}            last_event_price = price\n"
    f"{inner}            continue\n"
    f"{inner}        if side == 'SELL' and not (price < last_event_price):\n"
    f"{inner}            last_event_price = price\n"
    f"{inner}            continue\n"
    f"{inner}last_event_price = price\n"
)

post = s[m.end():]
s = pre + loop_line + inject + post

p.write_text(s, "utf-8")
print("PATCH ✅ Applied 1-candle reversal confirmation to backtest loop.")
print("Backup saved ✅", bak.name)
