import json, urllib.request, time, numpy as np

BASE_URL = "https://api.binance.us/api/v3/klines"

def fetch(days=365):
    end = int(time.time() * 1000)
    start = end - days * 24 * 60 * 60 * 1000
    data = []
    while start < end:
        url = f"{BASE_URL}?symbol=BTCUSDT&interval=5m&startTime={start}&limit=1000"
        raw = urllib.request.urlopen(url, timeout=10).read()
        batch = json.loads(raw)
        if not batch: break
        data.extend(batch)
        start = batch[-1][0] + 1
        time.sleep(0.15)
    return data

def aggregate(data, group):
    bars = []
    for i in range(0, len(data), group):
        chunk = data[i:i+group]
        if len(chunk) < group: break
        close_ = float(chunk[-1][4])
        bars.append(close_)
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

raw = fetch(365)
close_12h = aggregate(raw, 12*12)

r = rsi(close_12h, 14)

cash = 5000
fee_mult = 1 - 0.006
trades = 0

for i in range(len(close_12h)-1):
    if 60 <= r[i] < 70:
        ret = (close_12h[i+1] - close_12h[i]) / close_12h[i]
        cash *= (1 + ret) * fee_mult
        trades += 1

print("\n12H Long Bias (RSI 60–70)")
print("Trades:", trades)
print("Final Equity:", round(cash,2))
