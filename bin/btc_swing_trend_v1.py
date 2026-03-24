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
        raw = urllib.request.urlopen(url, timeout=12).read()
        batch = json.loads(raw)
        if not batch:
            break
        data.extend(batch)
        start = batch[-1][0] + 1
        time.sleep(0.05)
    closes = np.array([float(r[4]) for r in data], dtype=float)
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
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    avg_gain = np.zeros_like(arr)
    avg_loss = np.zeros_like(arr)
    if len(arr) <= length + 1:
        return np.zeros_like(arr)
    avg_gain[length] = gain[1:length+1].mean()
    avg_loss[length] = loss[1:length+1].mean()
    for i in range(length+1, len(arr)):
        avg_gain[i] = (avg_gain[i-1]*(length-1) + gain[i]) / length
        avg_loss[i] = (avg_loss[i-1]*(length-1) + loss[i]) / length
    rs = np.where(avg_loss == 0, np.inf, avg_gain / avg_loss)
    out = 100 - (100 / (1 + rs))
    out[:length] = 50.0
    return out

def aggregate_close(arr_5m, bars):
    out = []
    for i in range(0, len(arr_5m), bars):
        chunk = arr_5m[i:i+bars]
        if len(chunk) < bars:
            break
        out.append(chunk[-1])
    return np.array(out, dtype=float)

def rolling_high(arr, lookback):
    out = np.full_like(arr, np.nan)
    for i in range(lookback, len(arr)):
        out[i] = np.max(arr[i-lookback:i])
    return out

def rolling_low(arr, lookback):
    out = np.full_like(arr, np.nan)
    for i in range(lookback, len(arr)):
        out[i] = np.min(arr[i-lookback:i])
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=365)
    ap.add_argument("--bar-hours", type=int, default=12, choices=[12,24])
    ap.add_argument("--hold-bars", type=int, default=1)  # how many aggregated bars to hold
    ap.add_argument("--fee", type=float, default=0.006)  # friction per round-trip trade
    ap.add_argument("--start", type=float, default=5000.0)

    ap.add_argument("--ema-len", type=int, default=200)
    ap.add_argument("--rsi-long", type=float, default=65.0)
    ap.add_argument("--rsi-short", type=float, default=35.0)

    ap.add_argument("--mode", type=str, default="rsi", choices=["rsi","breakout"])
    ap.add_argument("--breakout-lb", type=int, default=20)  # lookback bars for breakout on aggregated series

    ap.add_argument("--max-dd-pct", type=float, default=0.0,
                    help="Stop trading if max drawdown percent exceeds this (0 disables).")

    ap.add_argument("--side", choices=["both","long","short"], default="both", help="Trade direction filter: both (default), long-only, or short-only.")
    args = ap.parse_args()

    closes_5m = fetch(args.days)
    bars_per_agg = (args.bar_hours * 60) // 5
    closes = aggregate_close(closes_5m, bars_per_agg)

    if len(closes) < max(args.ema_len + 5, 50):
        print("Not enough data after aggregation.")
        return 2

    e = ema(closes, args.ema_len)
    r = rsi(closes, 14)
    hi = rolling_high(closes, args.breakout_lb)
    lo = rolling_low(closes, args.breakout_lb)

    equity = args.start
    peak = equity
    max_dd = 0.0
    dd_cap_hit = False  # drawdown cap triggered?
    max_dd_pct = 0.0  # peak-to-trough drawdown percent
    trades = 0

    i = args.ema_len
    while i + args.hold_bars < len(closes):
        price = closes[i]

        # Regime gate (macro)
        up = price > e[i]
        dn = price < e[i]

        ret = None

        if args.mode == "rsi":
            if up and r[i] >= args.rsi_long:
                # long
                ret = (closes[i+args.hold_bars] - price) / price
            elif dn and r[i] <= args.rsi_short:
                # short
                ret = (price - closes[i+args.hold_bars]) / price

        else:  # breakout
            if up and not np.isnan(hi[i]) and price > hi[i]:
                # long breakout
                ret = (closes[i+args.hold_bars] - price) / price
            elif dn and not np.isnan(lo[i]) and price < lo[i]:
                # short breakdown
                ret = (price - closes[i+args.hold_bars]) / price

        if ret is None:
            i += 1
            continue

        net = ret - args.fee
        equity *= (1 + net)
        trades += 1

        if equity > peak:
            peak = equity
        dd = peak - equity
        dd_pct = (dd / peak * 100.0) if peak > 0 else 0.0
        if dd_pct > max_dd_pct:
            max_dd_pct = dd_pct
            # DD_CAP_FORGE_V1
            if getattr(args, 'max_dd_pct', 0.0) and float(args.max_dd_pct) > 0.0 and max_dd_pct >= float(args.max_dd_pct):
                dd_cap_hit = True
                print(f"DD_CAP_HIT: max_drawdown_pct={max_dd_pct:.2f} cap={float(args.max_dd_pct):.2f}")
                break

        if dd > max_dd:
            max_dd = dd

        # no overlap: jump to exit bar
        i += args.hold_bars

    print(f"\nSWING TREND v1 ({args.bar_hours}H bars, hold={args.hold_bars} bars, mode={args.mode})")
    print("Trades:", trades)
    print("start_cash:", round(args.start, 2))
    print("final_equity:", round(equity, 2))
    print("max_drawdown_usd:", round(max_dd, 2))
    print("max_drawdown_pct:", round(max_dd_pct, 2))
    print("dd_cap_hit:", dd_cap_hit)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
