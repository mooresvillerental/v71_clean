import json, urllib.request, shutil, subprocess, time
from pathlib import Path

BASE = "http://127.0.0.1:18092"

AI_THRESHOLD = 65          # gate only
MIN_TRADE_USD = 100
INTERVAL_MIN = 5
FETCH_LIMIT = 15

# POP-UP behavior
POPUP_ON_SPEAK = True
POPUP_URL = f"{BASE}/ui/opportunities.html?focus=top""
POPUP_COOLDOWN_SEC = 45
STATE_PATH = Path.home() / ".ez_last_popup.json"

COIN_NAMES = {
    "BTC": "Bitcoin",
    "ETH": "Ethereum",
    "XRP": "Ripple",
    "SOL": "Solana",
    "DOGE": "Dogecoin",
    "ADA": "Cardano",
    "AVAX": "Avalanche",
    "LINK": "Chainlink",
    "DOT": "Polkadot",
    "LTC": "Litecoin",
    "UNI": "Uniswap",
    "AAVE": "Aave",
    "BCH": "Bitcoin Cash",
    "ATOM": "Cosmos",
}

def _fmt_money_whole(x):
    try:
        return int(round(float(x)))
    except Exception:
        return None

def _coin_full_name(symbol: str) -> str:
    sym = (symbol or "").strip()
    base = sym.split("-", 1)[0].upper() if sym else ""
    return COIN_NAMES.get(base, base or "Unknown")

def _get_json(url: str, timeout=12):
    raw = urllib.request.urlopen(url, timeout=timeout).read().decode("utf-8", "replace")
    return json.loads(raw)

def _choose_opportunity(top_list):
    for o in (top_list or []):
        action = str(o.get("action") or "HOLD").strip().upper()
        if action not in ("BUY", "SELL"):
            continue

        ai = o.get("ai_confidence")
        base = o.get("base_confidence")

        conf = None
        if ai is not None:
            try: conf = int(round(float(ai)))
            except Exception: conf = None
        if conf is None and base is not None:
            try: conf = int(round(float(base)))
            except Exception: conf = None
        if conf is None or conf < AI_THRESHOLD:
            continue

        rec_usd = _fmt_money_whole(o.get("recommended_usd"))
        if rec_usd is None or rec_usd < MIN_TRADE_USD:
            continue

        return o, rec_usd

    return None, None

def build_phrase(o: dict, rec_usd: int) -> str:
    action = str(o.get("action") or "HOLD").strip().upper()
    coin = _coin_full_name(o.get("symbol"))
    # Your requested clean format (no confidence spoken)
    return f"EZTrader. {action}. {rec_usd} dollars. {coin}. EZTrader."

def speak(text: str) -> bool:
    tts = shutil.which("termux-tts-speak")
    if tts:
        subprocess.run([tts, text], check=False)
        return True
    print(text)
    return False

def _cooldown_ok(key: str) -> bool:
    now = int(time.time())
    try:
        st = json.loads(STATE_PATH.read_text("utf-8"))
    except Exception:
        st = {}
    last = int(st.get(key) or 0)
    if (now - last) < POPUP_COOLDOWN_SEC:
        return False
    st[key] = now
    try:
        STATE_PATH.write_text(json.dumps(st), encoding="utf-8")
    except Exception:
        pass
    return True

def popup(url: str):
    if not POPUP_ON_SPEAK:
        return
    opener = shutil.which("termux-open-url")
    if not opener:
        return
    # Prevent constant re-opening
    if not _cooldown_ok("last_popup"):
        return
        # EZ_POPUP_TS_V1
    try:
        import time as _t
        sep = "&" if ("?" in url) else "?"
        url = f"{url}{sep}ts={int(_t.time()*1000)}"
    except Exception:
        pass
    subprocess.Popen([opener, url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def main():
    url = f"{BASE}/opportunities?interval={INTERVAL_MIN}&limit={FETCH_LIMIT}&ts=tts"
    j = _get_json(url, timeout=12)
    top = j.get("top") or []

    o, rec_usd = _choose_opportunity(top)
    if not o:
        print(f"NO SPEAK: No BUY/SELL met ai_confidence >= {AI_THRESHOLD} and >= ${MIN_TRADE_USD}.")
        return 0

    phrase = build_phrase(o, rec_usd)
    spoke = speak(phrase)

    if spoke:
        # Pop Opportunities immediately so you can confirm ASAP
        popup(POPUP_URL)

    print("SPOKE:" if spoke else "PRINTED:", phrase)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
