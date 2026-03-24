#!/usr/bin/env python3
# 12H Short Bias test: when RSI is in a band (default 50-60), enter SHORT, hold 12H, exit.
# Self-contained: uses urllib + numpy only (no pandas).

import argparse, time, math
import numpy as np
import urllib.request, json

BINANCEUS = "https://api.binance.us/api/v3/klines"

def fetch_klines(symbol="BTCUSDT", interval="5m", start_ms=None, end_ms=None, limit=1000):
    qs = f"?symbol={symbol}&interval={interval}&limit={limit}"
    if start_ms is not None:
        qs += f"&startTime={int(start_ms)}"
    if end_ms is not None:
        qs += f"&endTime={int(end_ms)}"
    url = BINANCEUS + qs
    raw = urllib.request.urlopen(url, timeout=12).read().decode("utf-8", "replace")
    return json.loads(raw)

def load_candles(days=365, interval="5m"):
    # BinanceUS max limit 1000 per call; 5m => 288/day; need ~days*288 bars
    bars_per_day = 288
    want = int(days * bars_per_day)
    now_ms = int(time.time() * 1000)
    # walk backwards in chunks of 1000
    all_rows = []
    end_ms = None
    while len(all_rows) < want:
        rows = fetch_klines(start_ms=None, end_ms=end_ms, limit=1000)
        if not rows:
            break
        all_rows = rows + all_rows
        # next end_ms is just before earliest open_time
        earliest = rows[0][0]
        end_ms = int(earliest) - 1
        # safety
        if len(rows) < 10:
            break
        time.sleep(0.05)
        # stop if we have enough and the earliest is older than needed
        if len(all_rows) >= want:
            break
    # trim to last "want"
    all_rows = all_rows[-want:]
    # columns: open_time, open, high, low, close, volume, close_time, ...
    closes = np.array([float(r[4]) for r in all_rows], dtype=float)
    return closes

def rsi_wilder(closes, period=14):
    closes = np.asarray(closes, dtype=float)
    if len(closes) < period + 2:
        return np.full_like(closes, np.nan)
    diff = np.diff(closes)
    gains = np.where(diff > 0, diff, 0.0)
    losses = np.where(diff < 0, -diff, 0.0)

    rsi = np.full(closes.shape, np.nan, dtype=float)
    # initial averages
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    def calc_rsi(ag, al):
        if al == 0 and ag == 0:
            return 50.0
        if al == 0:
            return 100.0
        rs = ag / al
        return 100.0 - (100.0 / (1.0 + rs))

    rsi[period] = calc_rsi(avg_gain, avg_loss)

    ag, al = avg_gain, avg_loss
    for i in range(period + 1, len(closes)):
        g = gains[i - 1]
        l = losses[i - 1]
        ag = (ag * (period - 1) + g) / period
        al = (al * (period - 1) + l) / period
        rsi[i] = calc_rsi(ag, al)
    return rsi

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=365)
    ap.add_argument("--rsi-period", type=int, default=14)
    ap.add_argument("--rsi-lo", type=float, default=50.0)
    ap.add_argument("--rsi-hi", type=float, default=60.0)
    ap.add_argument("--hold-hours", type=float, default=12.0)
    ap.add_argument("--fee_slip_total", type=float, default=0.006)  # 0.6% total round-trip friction
    ap.add_argument("--start-cash", type=float, default=5000.0)
    args = ap.parse_args()

    closes = load_candles(days=args.days, interval="5m")
    rsi = rsi_wilder(closes, period=args.rsi_period)

    hold_bars = int(round(args.hold_hours * 12))  # 5m bars: 12/hour
    cash = float(args.start_cash)
    equity = cash
    peak = equity
    max_dd = 0.0
    trades = 0

    i = 0
    n = len(closes)
    while i + hold_bars < n:
        if np.isnan(rsi[i]):
            i += 1
            continue

        # Entry rule: RSI in [lo, hi]
        if args.rsi_lo <= rsi[i] <= args.rsi_hi:
            entry = closes[i]
            exitp = closes[i + hold_bars]

            # SHORT return
            gross_ret = (entry - exitp) / entry
            net_ret = gross_ret - args.fee_slip_total

            equity = equity * (1.0 + net_ret)
            trades += 1

            if equity > peak:
                peak = equity
            dd = peak - equity
            if dd > max_dd:
                max_dd = dd

            i += hold_bars  # no overlap: hold then look again
        else:
            i += 1

    print("")
    print(f"12H Short Bias (RSI {args.rsi_lo:.0f}–{args.rsi_hi:.0f})")
    print(f"Trades: {trades}")
    print(f"start_cash: {args.start_cash:.2f}")
    print(f"final_equity: {equity:.2f}")
    print(f"max_drawdown_usd: {max_dd:.2f}")

if __name__ == "__main__":
    main()
