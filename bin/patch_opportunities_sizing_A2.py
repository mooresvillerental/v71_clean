from pathlib import Path
import re, sys

p = Path("app/server.py")
s = p.read_text("utf-8", errors="replace")

MARK = "EZ_OPPORTUNITIES_ROUTE_V1"

if MARK not in s:
    print("PATCH FAILED: could not find", MARK)
    sys.exit(1)

# Don't double-patch
if "recommended_usd" in s and "recommended_qty" in s and "holding_qty" in s:
    print("Already patched ✅ (recommended_* fields found).")
    sys.exit(0)

# 1) In the opportunities route, after settings/watchlist are loaded, add pool+state read.
# We'll insert right before: opps = []
m_opps = re.search(rf'(^\s*#\s*{re.escape(MARK)}\s*\n^\s*if path == "/opportunities":.*?\n)(?P<ind>\s*)opps\s*=\s*\[\]\s*$', s, flags=re.M|re.S)
if not m_opps:
    # fallback: find the first "opps = []" after marker
    m2 = re.search(rf'^\s*#\s*{re.escape(MARK)}\s*$.*?^(?P<ind>\s*)opps\s*=\s*\[\]\s*$', s, flags=re.M|re.S)
    if not m2:
        print("PATCH FAILED: could not locate opportunities 'opps = []' block")
        sys.exit(1)
    ind = m2.group("ind")
    insert_at = m2.start()
else:
    ind = m_opps.group("ind")
    insert_at = m_opps.start() + len(m_opps.group(1))

inject_pool_state = f"""
{ind}    # --- A2: sizing inputs (pool + holdings) ---
{ind}    try:
{ind}        pool = float((_st or {{}}).get("tactical_pool_usd") or 0.0)
{ind}    except Exception:
{ind}        pool = 0.0
{ind}    if pool <= 0:
{ind}        pool = 5000.0  # safe fallback
{ind}
{ind}    # Read app state for holdings (paper holdings or real later)
{ind}    holdings = {{}}
{ind}    cash_state = None
{ind}    try:
{ind}        import json as _j
{ind}        from pathlib import Path as _P
{ind}        _ap = _P(APP_STATE_PATH)
{ind}        if _ap.exists():
{ind}            _stj = _j.loads(_ap.read_text("utf-8", errors="replace"))
{ind}            holdings = (_stj.get("holdings") or {{}}) if isinstance(_stj, dict) else {{}}
{ind}            cash_state = _stj.get("cash_usd") if isinstance(_stj, dict) else None
{ind}    except Exception:
{ind}        holdings = {{}}
{ind}        cash_state = None
{ind}
"""

# Insert only if we don't already have pool/holdings block
if "A2: sizing inputs" not in s:
    s = s[:insert_at] + inject_pool_state + s[insert_at:]

# 2) Add sizing logic right before each opps.append({ ... })
# We’ll target the section inside the for-loop where opps.append({...}) happens.
# Insert a block immediately before "opps.append({" if it's inside /opportunities.
pattern_append = r'(?m)^(?P<ind>\s*)opps\.append\(\{\s*$'
matches = list(re.finditer(pattern_append, s))
if not matches:
    print("PATCH FAILED: could not find 'opps.append({'")
    sys.exit(1)

# We only want to patch the one that belongs to /opportunities route; pick the first one AFTER the marker.
m_mark = re.search(rf'^\s*#\s*{re.escape(MARK)}\s*$', s, flags=re.M)
if not m_mark:
    print("PATCH FAILED: marker not found on its own line")
    sys.exit(1)
mark_pos = m_mark.start()

target = None
for m in matches:
    if m.start() > mark_pos:
        target = m
        break
if not target:
    print("PATCH FAILED: could not find opportunities opps.append after marker")
    sys.exit(1)

ind2 = target.group("ind")

inject_before_append = f"""{ind2}# --- A2: recommended sizing (LOCKED_UNTIL_EXIT ready) ---
{ind2}holding_qty = 0.0
{ind2}try:
{ind2}    holding_qty = float((holdings or {{}}).get(sym) or 0.0)
{ind2}except Exception:
{ind2}    holding_qty = 0.0
{ind2}
{ind2}# Simple tiering: higher score => larger allocation
{ind2}alloc_pct = 0.0
{ind2}try:
{ind2}    sc = float(score or 0.0)
{ind2}except Exception:
{ind2}    sc = 0.0
{ind2}
{ind2}if action == "BUY":
{ind2}    if sc >= 10: alloc_pct = 0.60
{ind2}    elif sc >= 6: alloc_pct = 0.40
{ind2}    elif sc >= 3: alloc_pct = 0.25
{ind2}    elif sc > 0: alloc_pct = 0.15
{ind2}    else: alloc_pct = 0.00
{ind2}elif action == "SELL":
{ind2}    # In LOCKED_UNTIL_EXIT, a SELL is typically an exit -> sell what you hold
{ind2}    alloc_pct = 1.00
{ind2}else:
{ind2}    alloc_pct = 0.00
{ind2}
{ind2}recommended_usd = 0.0
{ind2}recommended_qty = 0.0
{ind2}est_value_usd = 0.0
{ind2}
{ind2}try:
{ind2}    if action == "BUY":
{ind2}        recommended_usd = float(pool) * float(alloc_pct)
{ind2}        recommended_usd = max(0.0, recommended_usd)
{ind2}        if last and recommended_usd > 0:
{ind2}            recommended_qty = float(recommended_usd) / float(last)
{ind2}    elif action == "SELL":
{ind2}        recommended_qty = float(holding_qty) * float(alloc_pct)
{ind2}        if last and recommended_qty > 0:
{ind2}            recommended_usd = float(recommended_qty) * float(last)
{ind2}    est_value_usd = float(holding_qty) * float(last) if (last and holding_qty) else 0.0
{ind2}except Exception:
{ind2}    pass
"""

# Insert this block immediately before the target opps.append({ line, but only if not already present nearby.
if "A2: recommended sizing" not in s:
    s = s[:target.start()] + inject_before_append + s[target.start():]

# 3) Add new fields inside the dict (right after "symbol": sym, for minimal disruption)
# Find the first occurrence of '"symbol": sym,' after the marker and insert fields below it.
sym_field = re.search(rf'(^\s*"symbol"\s*:\s*sym\s*,\s*$)', s[m_mark.end():], flags=re.M)
if not sym_field:
    print('PATCH FAILED: could not find line: "symbol": sym, inside opportunities payload')
    sys.exit(1)

sym_insert_pos = m_mark.end() + sym_field.end()

field_block = f"""
{ind2}                "holding_qty": round(float(holding_qty), 10),
{ind2}                "est_value_usd": round(float(est_value_usd), 4),
{ind2}                "recommended_usd": round(float(recommended_usd), 4),
{ind2}                "recommended_qty": round(float(recommended_qty), 10),
"""

# Avoid double insert if user already has these keys
if '"recommended_usd"' not in s[m_mark.end():m_mark.end()+8000]:
    s = s[:sym_insert_pos] + field_block + s[sym_insert_pos:]

p.write_text(s, "utf-8")
print("OK ✅ A2 sizing patched into /opportunities (recommended_usd, recommended_qty, holding_qty).")
