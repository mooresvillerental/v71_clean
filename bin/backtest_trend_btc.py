import argparse
import json
import urllib.request
import time
import numpy as np

BASE_URL = "https://api.binance.us/api/v3/klines"

def fetch_klines(days=30):
    end = int(time.time() * 1000)
    start = end - days * 24 * 60 * 60 * 1000
    all_data = []

    while start < end:
        url = f"{BASE_URL}?symbol=BTCUSDT&interval=5m&startTime={start}&limit=1000"
        raw = urllib.request.urlopen(url, timeout=10).read()
        data = json.loads(raw)

        if not data:
            break

        all_data.extend(data)
        start = data[-1][0] + 1
        time.sleep(0.15)

    return all_data

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

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=180)
    parser.add_argument("--fee-bps", type=float, default=40)
    parser.add_argument("--slip-bps", type=float, default=20)
    args = parser.parse_args()

    raw = fetch_klines(days=args.days)

    one_hour = aggregate(raw, 12)
    four_hour = aggregate(raw, 48)

    close_1h = one_hour[:,3]
    high_1h  = one_hour[:,1]
    low_1h   = one_hour[:,2]

    close_4h = four_hour[:,3]

    ema_20 = ema(close_1h, 20)
    ema_100 = ema(close_1h, 100)
    ema_4h = ema(close_4h, 200)

    rsi_1h = rsi(close_1h, 14)
    atr_1h = atr(high_1h, low_1h, close_1h, 14)

    cash = 5000.0
    position = 0.0
    entry_price = 0.0
    fee_mult = 1 - (args.fee_bps + args.slip_bps) / 10000

    impulse_active = False

    for i in range(200, len(close_1h)):

        regime_bull = close_1h[i] > ema_4h[min(i//4, len(ema_4h)-1)]

        candle_range = high_1h[i] - low_1h[i]
        avg_range = np.mean(high_1h[i-20:i] - low_1h[i-20:i])

        # Detect impulse
        if (regime_bull and
            candle_range > 1.5 * avg_range and
            close_1h[i] > ema_100[i]):
            impulse_active = True

        if position == 0 and impulse_active:
            # Pullback entry
            if (close_1h[i] <= ema_20[i] and
                rsi_1h[i] > 45 and
                close_1h[i] > close_1h[i-1]):

                position = cash / close_1h[i]
                entry_price = close_1h[i]
                cash = 0
                impulse_active = False

        elif position > 0:
            stop = entry_price - 2.5 * atr_1h[i]
            if close_1h[i] < stop or not regime_bull:
                cash = position * close_1h[i] * fee_mult
                position = 0

    final_equity = cash if position == 0 else position * close_1h[-1]

    print("start_cash:", 5000.0)
    print("final_equity:", round(final_equity, 2))

if __name__ == "__main__":
    main()
