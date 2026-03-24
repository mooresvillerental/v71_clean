import json, urllib.request, shutil, subprocess, math

BASE = "http://127.0.0.1:18092"

# Your current preference:
AI_THRESHOLD = 65          # speak only if ai_confidence >= 65
MIN_TRADE_USD = 100        # don't speak tiny trades
INTERVAL_MIN = 5
FETCH_LIMIT = 15           # look at up to 15 opps and pick first qualifying

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
    """
    Pick the first opp that:
      - action is BUY or SELL
      - ai_confidence >= threshold (or base_confidence if ai missing)
      - recommended_usd exists and >= MIN_TRADE_USD
    """
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
        if conf is None:
            continue
        if conf < AI_THRESHOLD:
            continue

        rec_usd = _fmt_money_whole(o.get("recommended_usd"))
        if rec_usd is None or rec_usd < MIN_TRADE_USD:
            continue

        return o, conf, rec_usd

    return None, None, None

def build_phrase(o: dict, conf: int, rec_usd: int) -> str:
    action = str(o.get("action") or "HOLD").strip().upper()
    coin = _coin_full_name(o.get("symbol"))
    # Format requested: "EZTrader buy 5000 bitcoin" (plus confidence), and EZTrader at end.
    # Also no HOLD speech (handled before we get here).
    parts = []
    parts.append("EZTrader.")
    parts.append(action + ".")
    parts.append(f"{rec_usd} dollars.")
    parts.append(f"{coin}.")
    parts.append(f"Confidence {conf}.")
    parts.append("EZTrader.")
    return " ".join(parts)

def speak(text: str) -> bool:
    tts = shutil.which("termux-tts-speak")
    if tts:
        subprocess.run([tts, text], check=False)
        return True
    print(text)
    return False

def main():
    url = f"{BASE}/opportunities?interval={INTERVAL_MIN}&limit={FETCH_LIMIT}&ts=tts"
    j = _get_json(url, timeout=12)
    top = j.get("top") or []
    o, conf, rec_usd = _choose_opportunity(top)
    if not o:
        print(f"NO SPEAK: No BUY/SELL opportunity met ai_confidence >= {AI_THRESHOLD} and >= ${MIN_TRADE_USD}.")
        return 0

    phrase = build_phrase(o, conf, rec_usd)
    spoke = speak(phrase)
    print("SPOKE:" if spoke else "PRINTED:", phrase)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
