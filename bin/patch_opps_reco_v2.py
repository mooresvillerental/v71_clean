from pathlib import Path
import re, json, sys

p = Path("app/server.py")
s = p.read_text("utf-8", errors="replace")

MARK = "EZ_OPPORTUNITIES_ROUTE_V1"
m = re.search(r'^\s*#\s*' + re.escape(MARK) + r'\s*$', s, flags=re.M)
if not m:
    raise SystemExit("PATCH FAILED: opportunities marker not found (# EZ_OPPORTUNITIES_ROUTE_V1)")

start = m.end()

# Avoid double patch
if all(k in s for k in ["recommended_usd", "recommended_qty", "holding_qty", "est_value_usd"]):
    print("Already patched ✅ (reco fields already present)")
    sys.exit(0)

# Find first opps.append( after the marker (loose match)
m2 = re.search(r'opps\.append\s*\(', s[start:], flags=re.M)
if not m2:
    raise SystemExit("PATCH FAILED: could not find any opps.append( AFTER opportunities marker")

ins_at = start + m2.start()

# Determine indentation from the line containing opps.append
line_start = s.rfind("\n", 0, ins_at) + 1
indent = re.match(r'[ \t]*', s[line_start:ins_at]).group(0)

# We need _st to exist in opportunities; it does in your route.
preblock = (
    f"{indent}# --- sizing / holdings (read-only) ---\n"
    f"{indent}_hold_qty = 0.0\n"
    f"{indent}try:\n"
    f"{indent}    from app.paths import APP_STATE_PATH\n"
    f"{indent}    from pathlib import Path as _P\n"
    f"{indent}    _stp = _P(APP_STATE_PATH)\n"
    f"{indent}    if _stp.exists():\n"
    f"{indent}        _state = json.loads(_stp.read_text('utf-8'))\n"
    f"{indent}    else:\n"
    f"{indent}        _state = {{}}\n"
    f"{indent}    _h = _state.get('holdings') or {{}}\n"
    f"{indent}    _hold_qty = float(_h.get(sym) or 0.0)\n"
    f"{indent}except Exception:\n"
    f"{indent}    _hold_qty = 0.0\n"
    f"{indent}\n"
    f"{indent}_rec_usd = None\n"
    f"{indent}_rec_qty = None\n"
    f"{indent}try:\n"
    f"{indent}    _pool = float((_st.get('tactical_pool_usd') if isinstance(_st, dict) else None) or 0.0)\n"
    f"{indent}except Exception:\n"
    f"{indent}    _pool = 0.0\n"
    f"{indent}\n"
    f"{indent}# Recommendation rules (Phase 2):\n"
    f"{indent}# BUY  -> use tactical pool USD (qty = usd/price)\n"
    f"{indent}# SELL -> sell current holdings only (prevents fake sells)\n"
    f"{indent}if action == 'BUY' and _pool > 0:\n"
    f"{indent}    _rec_usd = _pool\n"
    f"{indent}    try:\n"
    f"{indent}        _rec_qty = float(_rec_usd) / float(last)\n"
    f"{indent}    except Exception:\n"
    f"{indent}        _rec_qty = None\n"
    f"{indent}elif action == 'SELL':\n"
    f"{indent}    if _hold_qty and _hold_qty > 0:\n"
    f"{indent}        _rec_qty = float(_hold_qty)\n"
    f"{indent}        _rec_usd = float(_hold_qty) * float(last)\n"
)

s = s[:ins_at] + preblock + "\n" + s[ins_at:]

# Insert new fields right after "reason": reason, but ONLY after the marker section
sub = s[start:]
mm = re.search(r'("reason"\s*:\s*reason\s*,\s*\n)', sub)
if not mm:
    raise SystemExit('PATCH FAILED: could not find `"reason": reason,` after opportunities marker')

inject = (
    mm.group(1)
    + '                "holding_qty": float(_hold_qty),\n'
    + '                "est_value_usd": (None if _hold_qty is None else round(float(_hold_qty) * float(last), 6)),\n'
    + '                "recommended_usd": (None if _rec_usd is None else round(float(_rec_usd), 2)),\n'
    + '                "recommended_qty": (None if _rec_qty is None else round(float(_rec_qty), 10)),\n'
)

sub = re.sub(r'("reason"\s*:\s*reason\s*,\s*\n)', lambda _m: inject, sub, count=1)
s = s[:start] + sub

p.write_text(s, "utf-8")
print("OK ✅ Patched /opportunities with reco + holdings fields (v2)")
