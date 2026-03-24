#!/usr/bin/env python3
from pathlib import Path
import re

p = Path("bin/backtest_90d_v1.py")
src = p.read_text(encoding="utf-8")

# 1) Ensure bin directory is on sys.path (so sibling imports work)
shim = (
    "import os, sys\n"
    "sys.path.insert(0, os.path.dirname(__file__))\n"
)

if "sys.path.insert(0, os.path.dirname(__file__))" not in src:
    # Insert after the very first import block line (after shebang/docstring, before other imports)
    # Find first "import ..." line
    m = re.search(r"(?m)^(import\s+\w+|from\s+\w+\s+import)\b", src)
    if not m:
        raise SystemExit("[FAIL] Could not find an import section to insert sys.path shim")
    insert_at = m.start()
    src = src[:insert_at] + shim + src[insert_at:]
    print("[OK] inserted sys.path shim")
else:
    print("[SKIP] sys.path shim already present")

# 2) Fix the regime import to be sibling-module import
src2 = src.replace(
    "from bin.regime_engine_v1 import RegimeConfig, build_regime_series, regime_multiplier, range_rsi_buy_threshold\n",
    "from regime_engine_v1 import RegimeConfig, build_regime_series, regime_multiplier, range_rsi_buy_threshold\n",
)
if src2 != src:
    src = src2
    print("[OK] fixed regime import to sibling module")
else:
    print("[SKIP] regime import already fixed or not found")

p.write_text(src, encoding="utf-8")
print("Done.")
