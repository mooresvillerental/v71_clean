import json
import time
from pathlib import Path

from app.ezcore_v1.core.config import CoreConfig
from app.ezcore_v1.core.engine import CoreV1

PRICE_FILE = Path("signals/latest_price.json")
SIGNAL_FILE = Path("signals/latest_signal.json")

cfg = CoreConfig()
engine = CoreV1(cfg)

prices = []
last_action = None
last_price_written = None

MIN_BARS = 220

def load_price():
    if not PRICE_FILE.exists():
        return None
    try:
        data = json.loads(PRICE_FILE.read_text())
        return float(data["price"])
    except Exception:
        return None

def write_signal(signal: dict):
    SIGNAL_FILE.write_text(json.dumps(signal, indent=2) + "\n", encoding="utf-8")

print("EZTRADER Live Engine running...")

while True:
    try:
        price = load_price()

        if price is None:
            time.sleep(2)
            continue

        prices.append(price)

        if len(prices) > 400:
            prices.pop(0)

        if len(prices) < MIN_BARS:
            if len(prices) % 25 == 0:
                print(f"Building history... {len(prices)}/{MIN_BARS}")
            time.sleep(2)
            continue

        closes_15m = prices[-220:]
        closes_1h = prices[-220:]

        sig = engine.strat_a.generate(
            "BTC-USD",
            closes_15m,
            closes_1h,
            price,
        )

        confidence = engine._simple_confidence_score(sig)

        trend = "Neutral"
        if str(sig.action).upper() == "BUY":
            trend = "Bullish"
        elif str(sig.action).upper() == "SELL":
            trend = "Bearish"

        signal = {
            "symbol": "BTC-USD",
            "action": sig.action,
            "price": price,
            "rsi": sig.rsi,
            "confidence": confidence,
            "risk_level": "Medium",
            "trend": trend,
            "suggested_trade_usd": 150,
            "timestamp": int(time.time()),
        }

        action_changed = signal["action"] != last_action
        price_moved = last_price_written is None or abs(price - last_price_written) >= 25.0

        if action_changed or (signal["action"] != "NONE" and price_moved):
            write_signal(signal)
            print("Signal:", signal)
            last_action = signal["action"]
            last_price_written = price

    except Exception as e:
        print("Engine error:", e)

    time.sleep(2)
