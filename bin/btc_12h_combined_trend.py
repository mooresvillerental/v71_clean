#!/usr/bin/env python3
import argparse, time, json, urllib.request
import numpy as np

BASE = "https://api.binance.us/api/v3/klines"

def fetch(days=365):
    end = int(time.time() * 1000)
    start = end - days * 24 * 60 * 60 * 1000
    data = []
    while start < end:
        url = f"{BASE}?symbol=BTCUSDT&interval=5m&startTime={start}&limit=1000"
        raw = urllib.request.urlopen(url, timeout=10).read()
        batch = json.loads(raw)
        if not batch:
            break
        data.extend(batch)
        start = batch[-1][0] + 1
        time.sleep(0.05)
    closes = np.array([float(r[4]) for r in data])
    return closes

def ema(arr, length):
    e = np.zeros_like(arr)
    k = 2 / (length + 1)
    e[0] = arr[0]
    for i in range(1, len(arr)):
        e[i] = arr[i] * k + e[i-1] * (1 - k)
    return e

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

def aggregate(arr, bars):
    out = []
    for i in range(0, len(arr), bars):
        chunk = arr[i:i+bars]
        if len(chunk) < bars:
            break
        out.append(chunk[-1])
    return np.array(out)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=365)
    ap.add_argument("--hold-hours", type=int, default=12)
    ap.add_argument("--fee", type=float, default=0.006)
    ap.add_argument("--start", type=float, default=5000)
    args = ap.parse_args()

    closes_5m = fetch(args.days)
    closes = aggregate(closes_5m, 12*12)  # 12H bars
    r = rsi(closes, 14)
    ema200 = ema(closes, 200)

    hold = 1  # 1 bar = 12H
    equity = args.start
    peak = equity
    max_dd = 0
    trades = 0

    i = 200
    while i + hold < len(closes):
        price = closes[i]

        # LONG: price above EMA200 AND RSI > 60
        if price > ema200[i] and r[i] > 60:
            ret = (closes[i+hold] - price) / price

        # SHORT: price below EMA200 AND RSI < 40
        elif price < ema200[i] and r[i] < 40:
            ret = (price - closes[i+hold]) / price

        else:
            i += 1
            continue

        net = ret - args.fee
        equity *= (1 + net)
        trades += 1

        if equity > peak:
            peak = equity
        dd = peak - equity
        if dd > max_dd:
            max_dd = dd

        i += hold

    print("\n12H Combined Trend Model")
    print("Trades:", trades)
    print("start_cash:", round(args.start,2))
    print("final_equity:", round(equity,2))
    print("max_drawdown_usd:", round(max_dd,2))

if __name__ == "__main__":
    main()
