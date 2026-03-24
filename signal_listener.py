import json
import time
from pathlib import Path

PRICE_FILE = Path("signals/latest_price.json")
OUT_FILE = Path("signals/latest_signal.json")

prices = []

def load_price():
    if not PRICE_FILE.exists():
        return None
    try:
        data = json.loads(PRICE_FILE.read_text())
        return float(data.get("price"))
    except:
        return None

print("Signal listener running...")

last_signal = None

while True:

    price = load_price()

    if price:

        prices.append(price)

        if len(prices) > 20:
            prices.pop(0)

        if len(prices) >= 10:

            short_avg = sum(prices[-5:]) / 5
            long_avg = sum(prices[-10:]) / 10

            if short_avg > long_avg:
                action = "BUY"
                trend = "Bullish"
                rsi = 45.0
            else:
                action = "SELL"
                trend = "Bearish"
                rsi = 70.0

            confidence = 60

            signal = {
                "symbol": "BTC-USD",
                "action": action,
                "price": price,
                "rsi": rsi,
                "confidence": confidence,
                "risk_level": "Medium",
                "trend": trend,
                "suggested_trade_usd": 150,
                "timestamp": int(time.time())
            }

            if action != last_signal:
                OUT_FILE.write_text(json.dumps(signal, indent=2))
                print("Signal updated:", signal)
                last_signal = action

    time.sleep(2)
