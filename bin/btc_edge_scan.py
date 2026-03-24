import json
import urllib.request
import time
import numpy as np

BASE_URL = "https://api.binance.us/api/v3/klines"

def fetch(days=180):
    end = int(time.time() * 1000)
    start = end - days * 24 * 60 * 60 * 1000
    data = []

    while start < end:
        url = f"{BASE_URL}?symbol=BTCUSDT&interval=5m&startTime={start}&limit=1000"
        raw = urllib.request.urlopen(url, timeout=10).read()
        batch = json.loads(raw)
        if not batch:
            break
        data.extend(batch)
        start = batch[-1][0] + 1
        time.sleep(0.15)

    return np.array([float(x[4]) for x in data])  # close prices

def forward_returns(prices, bars_ahead):
    returns = []
    for i in range(len(prices) - bars_ahead):
        r = (prices[i + bars_ahead] - prices[i]) / prices[i]
        returns.append(r)
    return np.array(returns)

prices = fetch(180)

horizons = {
    "1H": 12,
    "4H": 48,
    "12H": 144,
    "24H": 288
}

thresholds = [0.006, 0.01, 0.02, 0.03]

print("\nBTC Forward Return Distribution (180d)\n")

for name, bars in horizons.items():
    r = forward_returns(prices, bars)
    print(f"--- {name} ---")
    for t in thresholds:
        pct = np.mean(r > t) * 100
        print(f"Moves > {t*100:.1f}% : {pct:.2f}%")
    print()
