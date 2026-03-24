from pathlib import Path
import re

p = Path("bin/ez_speak_top_opportunity.py")
s = p.read_text("utf-8", errors="replace")

# Replace build_phrase() body safely (from def build_phrase ... up to next def speak)
pat = re.compile(r"def build_phrase\(o: dict\) -> str:\n(?s).*?\n(?=def speak\()", re.M)

m = pat.search(s)
if not m:
    raise SystemExit("PATCH FAILED: could not locate build_phrase() block")

new = """def build_phrase(o: dict) -> str:
    sym = (o.get("symbol") or "").strip()
    action = (o.get("action") or "HOLD").strip().upper()
    rec_usd = _fmt_money(o.get("recommended_usd"))
    rec_qty = _fmt_qty(o.get("recommended_qty"))

    # Speak-friendly symbol: "UNI-USD" -> "UNI"
    coin = sym.split("-", 1)[0] if sym else "UNKNOWN"

    # Required format: EZTrader first, then trade type and amount
    if action in ("BUY","SELL"):
        if rec_usd is not None:
            msg = f"EZTrader. {action}. {rec_usd} dollars. {coin}."
        else:
            msg = f"EZTrader. {action}. No amount. {coin}."
        if rec_qty is not None:
            msg += f" Estimated quantity {rec_qty}."
        return msg

    # HOLD / default
    return f"EZTrader. HOLD. {coin}."
"""

s2 = s[:m.start()] + new + "\n\n" + s[m.end():]
p.write_text(s2, "utf-8")
print("OK ✅ Updated TTS phrase order: EZTrader → action → amount → coin → qty")
