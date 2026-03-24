import json, urllib.request, shutil, subprocess, sys, math

BASE = "http://127.0.0.1:18092"

def _fmt_money(x):
    try:
        x = float(x)
    except Exception:
        return None
    # Whole dollars for TTS clarity
    return int(round(x))

def _fmt_qty(x):
    try:
        x = float(x)
    except Exception:
        return None
    # Keep a sane number of decimals for speech
    if x >= 100:  return round(x, 2)
    if x >= 10:   return round(x, 4)
    return round(x, 6)
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






def speak(text: str) -> bool:
    tts = shutil.which("termux-tts-speak")
    if tts:
        # -s rate (optional). Keep default unless you want faster later.
        subprocess.run([tts, text], check=False)
        return True
    # Fallback: just print
    print(text)
    return False

def main():
    url = f"{BASE}/opportunities?interval=5&limit=1&ts=tts"
    raw = urllib.request.urlopen(url, timeout=12).read().decode("utf-8", "replace")
    j = json.loads(raw)
    top = (j.get("top") or [])
    if not top:
        print("No opportunities returned.")
        return 2
    phrase = build_phrase(top[0])
    speak(phrase)
    # Also print for visibility/logs
    print("SPOKE:", phrase)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
