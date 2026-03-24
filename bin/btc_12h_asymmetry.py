import json
import urllib.request
import time
import numpy as np

BASE_URL = "https://api.binance.us/api/v3/klines"

def fetch(days=365):
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

    return data

def aggregate(data, group):
    bars = []
    for i in range(0, len(data), group):
        chunk = data[i:i+group]
        if len(chunk) < group:
            break
        open_ = float(chunk[0][1])
        high_ = max(float(c[2]) for c in chunk)
        low_  = min(float(c[3]) for c in chunk)
        close_ = float(chunk[-1][4])
        bars.append((open_, high_, low_, close_))
    return np.array(bars)

def rsi(arr, length=14):
    delta = np.diff(arr, prepend=arr[0])
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)

    avg_gain = np.zeros_like(arr)
    avg_loss = np.zeros_like(arr)

    avg_gain[length] = gain[1:length+1].mean()
    avg_loss[length] = loss[1:length+1].mean()

    for i in range(length+1, len(arr)):
        avg_gain[i] = (avg_gain[i-1]*(length-1) + gain[i]) / length
        avg_loss[i] = (avg_loss[i-1]*(length-1) + loss[i]) / length

    rs = np.where(avg_loss == 0, 0, avg_gain / avg_loss)
    return 100 - (100 / (1 + rs))

def forward_returns(prices, bars_ahead):
    returns = []
    for i in range(len(prices) - bars_ahead):
        r = (prices[i + bars_ahead] - prices[i]) / prices[i]
        returns.append(r)
    return np.array(returns)

print("\nFetching BTC data...")
raw = fetch(365)

bars_12h = aggregate(raw, 12*12)
close_12h = bars_12h[:,3]

print("Calculating RSI...")
rsi_vals = rsi(close_12h, 14)

print("Calculating 12H forward returns...")
fwd = forward_returns(close_12h, 1)

buckets = {
    "<30": (0,30),
    "30-40": (30,40),
    "40-50": (40,50),
    "50-60": (50,60),
    "60-70": (60,70),
    ">70": (70,100)
}

print("\n12H Conditional Forward Return Analysis (365d)\n")

for name, (low, high) in buckets.items():
    mask = (rsi_vals[:-1] >= low) & (rsi_vals[:-1] < high)
    subset = fwd[mask]

    if len(subset) == 0:
        continue

    avg = np.mean(subset) * 100
    p1 = np.mean(subset > 0.01) * 100
    p2 = np.mean(subset > 0.02) * 100
    p3 = np.mean(subset > 0.03) * 100

    print(f"RSI {name}")
    print(f"Count: {len(subset)}")
    print(f"Avg Return: {avg:.3f}%")
    print(f">%1%: {p1:.2f}% | >2%: {p2:.2f}% | >3%: {p3:.2f}%\n")
