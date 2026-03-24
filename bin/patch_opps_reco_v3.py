from pathlib import Path
import re, sys

p = Path("app/server.py")
s = p.read_text("utf-8", errors="replace")

MARK = "EZ_OPPORTUNITIES_ROUTE_V1"
m = re.search(r'^\s*#\s*' + re.escape(MARK) + r'\s*$', s, flags=re.M)
if not m:
    raise SystemExit("PATCH FAILED: opportunities marker not found")

start = m.start()
endm = re.search(r'^\s*# --- Chart endpoint: live price \(read-only\) ---\s*$', s[m.end():], flags=re.M)
if not endm:
    raise SystemExit("PATCH FAILED: could not find chart anchor after opportunities block")
end = m.end() + endm.start()

block = s[start:end]

if all(k in block for k in ["recommended_usd", "recommended_qty", "holding_qty", "est_value_usd"]):
    print("Already patched ✅ (reco fields already present in opportunities block)")
    sys.exit(0)

mo = re.search(r'(?m)^(?P<ind>[ \t]*)o\s*=\s*\{\s*$', block)
if not mo:
    raise SystemExit("PATCH FAILED: could not find `o = {` inside opportunities block")

ind = mo.group("ind")

pre = (
    f"{ind}# --- sizing / holdings (read-only) ---\n"
    f"{ind}_hold_qty = 0.0\n"
    f"{ind}try:\n"
    f"{ind}    appst = _read_json(APP_STATE_PATH) or {{}}\n"
    f"{ind}    h = appst.get('holdings') or {{}}\n"
    f"{ind}    _hold_qty = float(h.get(sym) or 0.0)\n"
    f"{ind}except Exception:\n"
    f"{ind}    _hold_qty = 0.0\n"
    f"{ind}\n"
    f"{ind}_est_value = None\n"
    f"{ind}try:\n"
    f"{ind}    _est_value = float(_hold_qty) * float(last)\n"
    f"{ind}except Exception:\n"
    f"{ind}    _est_value = None\n"
    f"{ind}\n"
    f"{ind}_rec_usd = None\n"
    f"{ind}_rec_qty = None\n"
    f"{ind}try:\n"
    f"{ind}    _pool = float((_st.get('tactical_pool_usd') if isinstance(_st, dict) else None) or 0.0)\n"
    f"{ind}except Exception:\n"
    f"{ind}    _pool = 0.0\n"
    f"{ind}\n"
    f"{ind}# Recommendation rules (Phase 2):\n"
    f"{ind}# BUY  -> use tactical pool USD (qty = usd/price)\n"
    f"{ind}# SELL -> sell current holdings only (prevents fake sells)\n"
    f"{ind}if action == 'BUY' and _pool > 0:\n"
    f"{ind}    _rec_usd = _pool\n"
    f"{ind}    try:\n"
    f"{ind}        _rec_qty = float(_rec_usd) / float(last)\n"
    f"{ind}    except Exception:\n"
    f"{ind}        _rec_qty = None\n"
    f"{ind}elif action == 'SELL':\n"
    f"{ind}    if _hold_qty and _hold_qty > 0:\n"
    f"{ind}        _rec_qty = float(_hold_qty)\n"
    f"{ind}        try:\n"
    f"{ind}            _rec_usd = float(_hold_qty) * float(last)\n"
    f"{ind}        except Exception:\n"
    f"{ind}            _rec_usd = None\n"
)

block2 = block[:mo.start()] + pre + "\n" + block[mo.start():]

inj_pat = r'(?m)^(?P<ind2>[ \t]*)"reason"\s*:\s*reason\s*,\s*$'
mi = re.search(inj_pat, block2)
if not mi:
    raise SystemExit('PATCH FAILED: could not find `"reason": reason,` inside opportunities dict')

ind2 = mi.group("ind2")
ins_lines = (
    f'{ind2}"holding_qty": round(float(_hold_qty), 10),\n'
    f'{ind2}"est_value_usd": (None if _est_value is None else round(float(_est_value), 6)),\n'
    f'{ind2}"recommended_usd": (None if _rec_usd is None else round(float(_rec_usd), 2)),\n'
    f'{ind2}"recommended_qty": (None if _rec_qty is None else round(float(_rec_qty), 10)),'
)

block2 = re.sub(inj_pat, lambda m_: m_.group(0) + "\n" + ins_lines, block2, count=1)

s2 = s[:start] + block2 + s[end:]
p.write_text(s2, "utf-8")
print("OK ✅ Patched /opportunities: holding_qty, est_value_usd, recommended_usd, recommended_qty")
