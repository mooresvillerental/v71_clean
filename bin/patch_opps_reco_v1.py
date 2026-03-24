from pathlib import Path
import re, json

p = Path("app/server.py")
s = p.read_text("utf-8", errors="replace")

MARK = "EZ_OPPORTUNITIES_ROUTE_V1"
m = re.search(r'^\s*#\s*' + re.escape(MARK) + r'\s*$', s, flags=re.M)
if not m:
    raise SystemExit("PATCH FAILED: opportunities marker not found")

pat = r'("reason"\s*:\s*reason\s*,\s*\n)'
mm = re.search(pat, s)
if not mm:
    raise SystemExit('PATCH FAILED: could not find `"reason": reason,` pattern to anchor insertion')

if "recommended_usd" in s and "holding_qty" in s and "est_value_usd" in s:
    print("Already patched ✅")
    raise SystemExit(0)

insert = (
    mm.group(1)
    + '                "holding_qty": float(_hold_qty),\n'
    + '                "est_value_usd": (None if _hold_qty is None else round(float(_hold_qty) * float(last), 6)),\n'
    + '                "recommended_usd": (None if _rec_usd is None else round(float(_rec_usd), 2)),\n'
    + '                "recommended_qty": (None if _rec_qty is None else round(float(_rec_qty), 10)),\n'
)

pat2 = r'^\s*opps\.append\(\{\s*$'
m2 = re.search(pat2, s, flags=re.M)
if not m2:
    raise SystemExit("PATCH FAILED: could not find opps.append({ line")

line_start = s.rfind("\n", 0, m2.start()) + 1
indent = re.match(r'\s*', s[line_start:m2.start()]).group(0)

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

s = s[:m2.start()] + preblock + "\n" + s[m2.start():]
s = re.sub(pat, lambda _m: insert, s, count=1)

p.write_text(s, "utf-8")
print("OK ✅ Patched /opportunities reco fields")
