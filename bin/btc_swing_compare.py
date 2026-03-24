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

def ema(arr, length):
    out = np.zeros_like(arr)
    alpha = 2 / (length + 1)
    out[0] = arr[0]
    for i in range(1, len(arr)):
        out[i] = alpha * arr[i] + (1 - alpha) * out[i-1]
    return out

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

def atr(high, low, close, length=14):
    tr = np.maximum(high - low,
         np.maximum(np.abs(high - np.roll(close,1)),
                    np.abs(low - np.roll(close,1))))
    out = np.zeros_like(close)
    out[length] = tr[1:length+1].mean()
    for i in range(length+1, len(close)):
        out[i] = (out[i-1]*(length-1) + tr[i]) / length
    return out

def run_model(bars, label):
    close = bars[:,3]
    high  = bars[:,1]
    low   = bars[:,2]

    ema50 = ema(close, 50)
    ema200 = ema(close, 200)
    rsi14 = rsi(close, 14)
    atr14 = atr(high, low, close, 14)

    cash = 5000.0
    position = 0.0
    entry_price = 0.0
    fee_mult = 1 - 0.006  # 0.6% friction

    trades = 0

    for i in range(200, len(close)):

        regime = close[i] > ema200[i]

        if position == 0:
            if regime and close[i] > ema50[i] and rsi14[i-1] <= 55 and rsi14[i] > 55:
                position = cash / close[i]
                entry_price = close[i]
                cash = 0
                trades += 1
        else:
            stop = entry_price - 2.5 * atr14[i]
            if close[i] < stop or not regime:
                cash = position * close[i] * fee_mult
                position = 0

    final = cash if position == 0 else position * close[-1]

    print(f"\n--- {label} ---")
    print("Trades:", trades)
    print("Final Equity:", round(final,2))

data = fetch(365)

bars_12h = aggregate(data, 12*12)
bars_24h = aggregate(data, 24*12)

run_model(bars_12h, "12H Model")
run_model(bars_24h, "24H Model")
