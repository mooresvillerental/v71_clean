from pathlib import Path
import re, sys

p = Path("app/server.py")
s = p.read_text("utf-8", errors="replace")

# Find the opportunities route marker
mark = "EZ_OPPORTUNITIES_ROUTE_V1"
m = re.search(r'^\s*#\s*' + re.escape(mark) + r'\s*$', s, flags=re.M)
if not m:
    print("PATCH FAILED: opportunities marker not found:", mark)
    sys.exit(1)

# We will patch inside the opportunities block by:
# 1) reading holdings_qty from portfolio payload helper (_build_portfolio_payload)
# 2) marking each symbol as holding/not_holding
# 3) setting actionable based on holding state + action

# Locate the start of the opportunities 'if path == "/opportunities":' within the block
m_if = re.search(r'^\s*if path == "/opportunities":\s*$', s[m.start():], flags=re.M)
if not m_if:
    print("PATCH FAILED: could not find opportunities route line")
    sys.exit(1)

# Determine indentation of route lines (same as other routes)
ind_route = re.search(r'^(?P<ind>\s*)if path == "/opportunities":\s*$', s, flags=re.M).group("ind")

# Insert after syms resolution (right after 'if not syms:' fallback block)
needle = r'^\s*if not syms:\s*$'
m2 = re.search(needle, s[m.start():], flags=re.M)
if not m2:
    print("PATCH FAILED: could not find 'if not syms:' inside opportunities")
    sys.exit(1)

# We need a safer insertion point: after the whole syms fallback section.
# We'll insert right before PAIR = { ... } line which exists in your opportunities block.
m_pair = re.search(r'^\s*PAIR\s*=\s*\{', s[m.start():], flags=re.M)
if not m_pair:
    print("PATCH FAILED: could not find PAIR map inside opportunities")
    sys.exit(1)

insert_at = m.start() + m_pair.start()

inject = f'''
{ind_route}    # --- Position Intelligence (A1) ---
{ind_route}    # Build holdings map from portfolio snapshot (qty > 0 => holding)
{ind_route}    holdings = {{}}
{ind_route}    try:
{ind_route}        snap = _build_portfolio_payload(_st) if "_st" in locals() else _build_portfolio_payload({{}})
{ind_route}        holdings = (snap or {{}}).get("holdings_qty") or {{}}
{ind_route}    except Exception:
{ind_route}        holdings = {{}}

{ind_route}    def _qty(sym: str) -> float:
{ind_route}        try:
{ind_route}            return float((holdings or {{}}).get(sym) or 0.0)
{ind_route}        except Exception:
{ind_route}            return 0.0
'''

s = s[:insert_at] + inject + s[insert_at:]

# Patch where opps.append({...}) occurs to add position + actionable
# We locate the opps.append({ line inside opportunities and inject fields.
pat = r'opps\.append\(\{\s*'
m3 = re.search(pat, s[m.start():], flags=re.M)
if not m3:
    print("PATCH FAILED: could not find opps.append({ inside opportunities")
    sys.exit(1)

# Find the dict body start line and inject after "symbol": sym,
# We'll do a simple replace of '"symbol": sym,' first occurrence after marker.
sub_from = '"symbol": sym,'
sub_to = '"symbol": sym,\n' + \
         f'{ind_route}                "position": ("HOLDING" if _qty(sym) > 0 else "FLAT"),\n' + \
         f'{ind_route}                "actionable": ( (action=="BUY" and _qty(sym)<=0) or (action=="SELL" and _qty(sym)>0) ),'

# Replace only once after marker
block = s[m.start():]
if sub_from not in block:
    print("PATCH FAILED: could not find symbol field inside opportunities payload")
    sys.exit(1)

block2 = block.replace(sub_from, sub_to, 1)
s = s[:m.start()] + block2

p.write_text(s, "utf-8")
print("OK ✅ Position Intelligence A1 patched into /opportunities")
