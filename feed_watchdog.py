import time
import json
import os
from pathlib import Path

PRICE_FILE = Path("signals/latest_price.json")
CHECK_SECONDS = 5
STALE_SECONDS = 20

last_price = None
last_change_time = time.time()

print("EZTRADER Feed Watchdog running...")

while True:
    try:
        if PRICE_FILE.exists():
            data = json.loads(PRICE_FILE.read_text())
            price = data.get("price")

            if price != last_price:
                last_price = price
                last_change_time = time.time()

            else:
                if time.time() - last_change_time > STALE_SECONDS:
                    print("PRICE STALE — restarting Kraken feed")

                    os.system("pkill -f kraken_ohlc_engine.py")
                    time.sleep(1)

                    os.system(
                        "cd ~/v71_clean && nohup python -u kraken_ohlc_engine.py > kraken_ohlc_engine.log 2>&1 &"
                    )

                    last_change_time = time.time()

    except Exception as e:
        print("Watchdog error:", e)

    time.sleep(CHECK_SECONDS)
