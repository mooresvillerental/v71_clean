from pathlib import Path
import re, sys

p = Path("app/server.py")
s = p.read_text("utf-8", errors="replace")

MARK = "EZ_OPPORTUNITIES_ROUTE_V1"
if MARK not in s:
    print("PATCH FAILED: marker not found:", MARK)
    sys.exit(1)

# Work only inside the opportunities route section by finding the block and patching its first opps.append dict.
m_mark = re.search(rf'^\s*#\s*{re.escape(MARK)}\s*$', s, flags=re.M)
if not m_mark:
    print("PATCH FAILED: marker line not found")
    sys.exit(1)

# Find the first "opps.append({" after marker
m_append = re.search(r'(?m)^(?P<ind>\s*)opps\.append\(\{\s*$', s[m_mark.end():])
if not m_append:
    print("PATCH FAILED: could not find opps.append({ after marker")
    sys.exit(1)

append_pos = m_mark.end() + m_append.start()
ind = m_append.group("ind")

# 1) Ensure default sizing vars exist right before opps.append
need_defaults = "A2_FORCE_DEFAULTS_V1"
if need_defaults not in s[m_mark.end():m_mark.end()+12000]:
    defaults = f"""{ind}# {need_defaults}
{ind}holding_qty = 0.0
{ind}est_value_usd = 0.0
{ind}recommended_usd = 0.0
{ind}recommended_qty = 0.0

{ind}try:
{ind}    # Holdings from app state (paper now, real later)
{ind}    holding_qty = float((holdings or {{}}).get(sym) or 0.0)
{ind}except Exception:
{ind}    holding_qty = 0.0

{ind}try:
{ind}    est_value_usd = float(holding_qty) * float(last) if (holding_qty and last) else 0.0
{ind}except Exception:
{ind}    est_value_usd = 0.0

{ind}try:
{ind}    if action == "BUY":
{ind}        # If you later change tiering, this remains the one source of truth.
{ind}        alloc_pct = 0.0
{ind}        sc = float(score or 0.0)
{ind}        if sc >= 10: alloc_pct = 0.60
{ind}        elif sc >= 6: alloc_pct = 0.40
{ind}        elif sc >= 3: alloc_pct = 0.25
{ind}        elif sc > 0: alloc_pct = 0.15
{ind}        recommended_usd = float(pool) * float(alloc_pct)
{ind}        if last and recommended_usd > 0:
{ind}            recommended_qty = float(recommended_usd) / float(last)
{ind}    elif action == "SELL":
{ind}        # LOCKED_UNTIL_EXIT: exit sizing = sell what you hold
{ind}        recommended_qty = float(holding_qty)
{ind}        if last and recommended_qty > 0:
{ind}            recommended_usd = float(recommended_qty) * float(last)
{ind}except Exception:
{ind}    pass

"""
    s = s[:append_pos] + defaults + s[append_pos:]

# Re-find opps.append after insertion (positions shifted)
m_append2 = re.search(r'(?m)^(?P<ind>\s*)opps\.append\(\{\s*$', s[m_mark.end():])
append_pos = m_mark.end() + m_append2.start()
ind = m_append2.group("ind")

# 2) Insert fields into the dict. We insert right after the "symbol": sym, line if present, else after opening.
# Find the dict start and end.
m_dict_start = re.search(r'(?m)^\s*opps\.append\(\{\s*$', s[append_pos:])
if not m_dict_start:
    print("PATCH FAILED: dict start not found (unexpected)")
    sys.exit(1)

dict_start = append_pos + m_dict_start.end()

# Find a good insertion spot inside that dict: after "symbol": sym,
m_symline = re.search(r'(?m)^(?P<ii>\s*)"symbol"\s*:\s*sym\s*,\s*$', s[dict_start:dict_start+3000])
insert_at = dict_start
ii = ind + "    "
if m_symline:
    insert_at = dict_start + m_symline.end()
    ii = m_symline.group("ii")

fields = f"""
{ii}"holding_qty": round(float(holding_qty), 10),
{ii}"est_value_usd": round(float(est_value_usd), 4),
{ii}"recommended_usd": round(float(recommended_usd), 4),
{ii}"recommended_qty": round(float(recommended_qty), 10),
"""

# Avoid double insert
window = s[m_mark.end():m_mark.end()+15000]
if '"recommended_usd"' not in window:
    s = s[:insert_at] + fields + s[insert_at:]

p.write_text(s, "utf-8")
print("OK ✅ A2-FIX applied: opportunities now always returns sizing fields.")
