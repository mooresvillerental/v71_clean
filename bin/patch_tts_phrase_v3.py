from pathlib import Path
import re

p = Path("bin/ez_speak_top_opportunity.py")
s = p.read_text("utf-8", errors="replace")

m1 = re.search(r'^\s*def build_phrase\(o: dict\) -> str:\s*$', s, flags=re.M)
m2 = re.search(r'^\s*def speak\(', s, flags=re.M)

if not m1 or not m2 or m2.start() <= m1.start():
    raise SystemExit("PATCH FAILED: could not locate build_phrase() boundaries")

new_func = r'''
def build_phrase(o: dict) -> str:
    sym = (o.get("symbol") or "").strip()
    action = (o.get("action") or "HOLD").strip().upper()

    rec_usd = _fmt_money(o.get("recommended_usd"))

    coin = sym.split("-", 1)[0] if sym else "UNKNOWN"

    # Confidence from score
    try:
        score = float(o.get("score") or 0.0)
    except Exception:
        score = 0.0

    if score >= 10.0:
        conf = "HIGH"
    elif score >= 5.0:
        conf = "MEDIUM"
    else:
        conf = "LOW"

    parts = []
    parts.append("EZTrader.")
    parts.append("Tactical " + action + ".")
    parts.append(f"{coin}.")

    if action in ("BUY","SELL"):
        if rec_usd is not None:
            parts.append(f"{rec_usd} dollars.")
        else:
            parts.append("No amount.")

    parts.append("Confidence " + conf + ".")
    return " ".join(parts).strip()
'''.lstrip("\n")

out = s[:m1.start()] + new_func + "\n\n" + s[m2.start():]
p.write_text(out, "utf-8")
print("OK ✅ Quantity removed from speech")
