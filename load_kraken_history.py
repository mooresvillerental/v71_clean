import requests
import json
from pathlib import Path

HISTORY_FILE = Path("signals/history_seed.json")

def load_ohlc(pair, interval):
    url = f"https://api.kraken.com/0/public/OHLC?pair={pair}&interval={interval}"
    r = requests.get(url, timeout=10)
    data = r.json()
    key = list(data["result"].keys())[0]
    candles = data["result"][key]
    closes = [float(c[4]) for c in candles]
    return closes

print("Downloading Kraken history...")

closes_15m = load_ohlc("XBTUSD", 15)
closes_1h = load_ohlc("XBTUSD", 60)

seed = {
    "closes_15m": closes_15m[-300:],
    "closes_1h": closes_1h[-300:]
}

HISTORY_FILE.write_text(json.dumps(seed, indent=2))

print("History saved.")
print("15m candles:", len(seed["closes_15m"]))
print("1h candles:", len(seed["closes_1h"]))
