from pathlib import Path
import re

p = Path("bin/ez_speak_top_opportunity.py")
s = p.read_text("utf-8", errors="replace")

m1 = re.search(r'^\s*def build_phrase\(o: dict\) -> str:\s*$', s, flags=re.M)
m2 = re.search(r'^\s*def speak\(', s, flags=re.M)

if not m1 or not m2 or m2.start() <= m1.start():
    raise SystemExit("PATCH FAILED: could not locate build_phrase() and def speak() boundaries")

new_func = r'''
def build_phrase(o: dict) -> str:
    sym = (o.get("symbol") or "").strip()
    action = (o.get("action") or "HOLD").strip().upper()

    # Money / qty (already in file)
    rec_usd = _fmt_money(o.get("recommended_usd"))
    rec_qty = _fmt_qty(o.get("recommended_qty"))

    # Speak-friendly symbol: "UNI-USD" -> "UNI"
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

    # Required format: EZTrader first, then Tactical + trade type + amount
    parts = []
    parts.append("EZTrader.")
    parts.append("Tactical " + action + ".")
    parts.append(f"{coin}.")
    if action in ("BUY","SELL"):
        if rec_usd is not None:
            parts.append(f"{rec_usd} dollars.")
        else:
            parts.append("No amount.")
        if rec_qty is not None:
            parts.append(f"Estimated quantity {rec_qty}.")
    parts.append("Confidence " + conf + ".")
    return " ".join(parts).strip()
'''.lstrip("\n")

out = s[:m1.start()] + new_func + "\n\n" + s[m2.start():]
p.write_text(out, "utf-8")
print("OK ✅ Updated build_phrase(): Tactical + Confidence")
