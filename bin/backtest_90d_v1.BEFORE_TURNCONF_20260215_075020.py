import json, time, math, csv, urllib.request
from pathlib import Path
from datetime import datetime, timezone

INTERVAL_MIN = 5
DAYS = 90
START_CASH = 5000.0  # starting simulated cash (change later if you want)
TRADE_PCT = 0.30     # 30%

def _apply_fee_slip(price: float, side: str, fee_bps: float, slip_bps: float) -> float:
    # side: BUY pays up; SELL receives down
    # bps: 10 = 0.10%
    m = 1.0 + (fee_bps + slip_bps) / 10000.0
    if (side or "").upper() == "BUY":
        return float(price) * m
    return float(price) / m


MIN_TRADE_USD = 100.0

SETTINGS_PATH = Path("/data/data/com.termux/files/home/v71_app_data/settings.json")

PAIR = {
  "BTC-USD":"XBTUSD","ETH-USD":"ETHUSD","SOL-USD":"SOLUSD","DOGE-USD":"DOGEUSD","XRP-USD":"XRPUSD",
  "ADA-USD":"ADAUSD","AVAX-USD":"AVAXUSD","LINK-USD":"LINKUSD","DOT-USD":"DOTUSD","LTC-USD":"LTCUSD",
  "UNI-USD":"UNIUSD","AAVE-USD":"AAVEUSD","BCH-USD":"BCHUSD","ATOM-USD":"ATOMUSD",
}

DEFAULT_WATCH = ["BTC-USD","ETH-USD","SOL-USD","XRP-USD","DOGE-USD","ADA-USD","AVAX-USD","LINK-USD","DOT-USD","LTC-USD","UNI-USD","AAVE-USD","BCH-USD","ATOM-USD"]

def load_settings():
    try:
        if SETTINGS_PATH.exists():
            return json.loads(SETTINGS_PATH.read_text("utf-8"))
    except Exception:
        pass
    return {}

def rsi_series(closes, period=14):
    n = len(closes)
    out = [None]*n
    if n < period+2:
        return out
    gains = [0.0]*n
    losses = [0.0]*n
    for i in range(1, n):
        d = closes[i]-closes[i-1]
        if d >= 0:
            gains[i]=d
        else:
            losses[i]=-d
    avg_gain = sum(gains[1:period+1])/period
    avg_loss = sum(losses[1:period+1])/period
    out[period] = 100.0 if avg_loss==0 else (100.0 - (100.0/(1.0+(avg_gain/avg_loss))))
    for i in range(period+1, n):
        avg_gain = (avg_gain*(period-1) + gains[i]) / period
        avg_loss = (avg_loss*(period-1) + losses[i]) / period
        out[i] = 100.0 if avg_loss==0 else (100.0 - (100.0/(1.0+(avg_gain/avg_loss))))
    return out

def build_signals(times, closes, lo=30.0, hi=70.0):
    rsis = rsi_series(closes, 14)
    sigs = []  # (t, side, price, rsi)
    prev = None
    for i in range(len(closes)):
        r = rsis[i]
        if r is None:
            continue
        if prev is not None:
            if prev >= lo and r < lo:
                sigs.append((times[i], "BUY", closes[i], float(r)))
            elif prev <= hi and r > hi:
                sigs.append((times[i], "SELL", closes[i], float(r)))
        prev = r
    return sigs

def fetch_ohlc(pair, interval_min, since_ts):
    url = f"https://api.kraken.com/0/public/OHLC?pair={pair}&interval={int(interval_min)}&since={int(since_ts)}"
    raw = urllib.request.urlopen(url, timeout=12).read().decode("utf-8","replace")
    j = json.loads(raw) if raw else {}
    res = (j.get("result") or {})
    ohlc = None
    for k,v in res.items():
        if k=="last": continue
        if isinstance(v, list):
            ohlc = v
            break
    if not ohlc:
        return [], []
    times, closes = [], []
    for row in ohlc:
        try:
            t = int(row[0]); c = float(row[4])
            times.append(t); closes.append(c)
        except Exception:
            continue
    return times, closes

def fmt_ts(t):
    return datetime.fromtimestamp(int(t), tz=timezone.utc).strftime("%Y-%m-%d %H:%M")

def main():
    # EZ_RSI_ARGS_V1
    # Parse RSI thresholds from CLI (defaults match classic 30/70)
    import argparse
    _p = argparse.ArgumentParser(add_help=False)
    _p.add_argument("--rsi-buy", type=float, default=30.0)
    _p.add_argument("--rsi-sell", type=float, default=70.0)
    
    # EZ_FEE_SLIP_ARGS_V1
    _p.add_argument("--fee-bps", type=float, default=0.0)   # per-side fee (bps)
    _p.add_argument("--slip-bps", type=float, default=0.0)  # per-side slippage (bps)
    _a, _unknown = _p.parse_known_args()
    rsi_buy = float(_a.rsi_buy)
    rsi_sell = float(_a.rsi_sell)
    fee_bps = float(_a.fee_bps)
    slip_bps = float(_a.slip_bps)

    st = load_settings()
    watch = []
    try:
        watch = list(st.get("portfolio_symbols") or [])
    except Exception:
        watch = []
    # normalize + filter
    norm = []
    seen = set()
    for s in (watch or DEFAULT_WATCH):
        s = (s or "").strip().upper()
        if s in ("BTCUSD","XBTUSD","XBT-USD"): s="BTC-USD"
        if s in ("ETHUSD",): s="ETH-USD"
        if s in ("XRPUSD",): s="XRP-USD"
        if s and s in PAIR and s not in seen:
            seen.add(s); norm.append(s)
    watch = norm[:15]  # keep it safe for phone

    pool_cap = float(st.get("tactical_pool_usd") or 5000.0)

    now = int(time.time())
    since = now - DAYS*24*3600

    data = {}
    for sym in watch:
        pair = PAIR[sym]
        times, closes = fetch_ohlc(pair, INTERVAL_MIN, since)
        if len(times) < 50:
            continue
        sigs = build_signals(times, closes, float(rsi_buy), float(rsi_sell))
        data[sym] = {"times": times, "closes": closes, "sigs": sigs}

    if not data:
        print("No candle data returned. Try again later.")
        return 2

    # Build merged event list of BUY/SELL signals
    events = []  # (t, sym, side, price, rsi, confidence)
    for sym, d in data.items():
        for (t, side, price, rsi) in d["sigs"]:
            conf = 0.0
            if side=="BUY":
                conf = max(0.0, float(rsi_buy) - rsi)   # deeper oversold => higher   # deeper oversold => higher
            elif side=="SELL":
                conf = max(0.0, rsi - float(rsi_sell))  # more overbought => higher   # more overbought => higher
            events.append((t, sym, side, price, rsi, conf))
    events.sort(key=lambda x: x[0])

    cash = float(START_CASH)
    pos_sym = None
    pos_qty = 0.0
    entry = None

    trades = []
    equity = []
    peak = cash
    max_dd = 0.0

    def mark_equity(t, px=None):
        nonlocal peak, max_dd
        eq = cash
        if pos_sym and px is not None:
            eq = cash + pos_qty*px
        equity.append((t, eq))
        peak = max(peak, eq)
        dd = (peak - eq)
        max_dd = max(max_dd, dd)

    # quick price lookup: use last close at/near time
    def price_at(sym, t):
        d = data[sym]
        times = d["times"]; closes = d["closes"]
        # binary-ish scan from end (good enough on phone)
        i = len(times)-1
        while i>0 and times[i] > t:
            i -= 1
        return closes[i]

    for (t, sym, side, price, rsi, conf) in events:
        # keep equity curve updated using held symbol price
        if pos_sym:
            mark_equity(t, price_at(pos_sym, t))
        else:
            mark_equity(t, None)

        if pos_sym is None:
            if side != "BUY":
                continue
            # if multiple buys at same timestamp, take the highest confidence
            same_t = [e for e in events if e[0]==t and e[2]=="BUY"]
            best = max(same_t, key=lambda x: x[5])
            if best[1] != sym:
                continue

            # sizing
            usd = max(MIN_TRADE_USD, cash*TRADE_PCT)
            usd = min(usd, pool_cap, cash)
            if usd < MIN_TRADE_USD:
                continue
            qty = usd / price
            pos_sym = sym
            pos_qty = qty
            cash -= usd
            entry = price
            trades.append((t, sym, "BUY", price, qty, usd, rsi))
        else:
            # only sell if sell signal for held symbol
            if sym != pos_sym or side != "SELL":
                continue
            usd = pos_qty * price
            cash += usd
            pnl = (price - entry) * pos_qty if entry is not None else 0.0
            trades.append((t, sym, "SELL", price, pos_qty, usd, rsi, pnl))
            pos_sym = None
            pos_qty = 0.0
            entry = None

    # final mark
    t_end = events[-1][0]
    if pos_sym:
        mark_equity(t_end, price_at(pos_sym, t_end))
    else:
        mark_equity(t_end, None)

    out_dir = Path("backtests")
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    trades_csv = out_dir / f"trades_90d_{stamp}.csv"
    equity_csv = out_dir / f"equity_90d_{stamp}.csv"

    with trades_csv.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["utc_time","symbol","side","price","qty","usd","rsi","pnl_usd"])
        for tr in trades:
            if tr[2]=="BUY":
                (t,s,side,px,qty,usd,rsi) = tr
                w.writerow([fmt_ts(t),s,side,px,qty,usd,rsi,""])
            else:
                (t,s,side,px,qty,usd,rsi,pnl) = tr
                w.writerow([fmt_ts(t),s,side,px,qty,usd,rsi,pnl])

    with equity_csv.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["utc_time","equity_usd"])
        for (t,eq) in equity:
            w.writerow([fmt_ts(t), eq])

    sells = [t for t in trades if t[2]=="SELL"]
    wins = [t for t in sells if (len(t)>=8 and t[7] > 0)]
    winrate = (len(wins)/len(sells)*100.0) if sells else 0.0

    final_eq = equity[-1][1] if equity else cash
    print("=== EZTrader Backtest (90d, 5m, LOCKED_UNTIL_EXIT) ===")
    print("symbols_used:", len(data), data.keys())
    print("start_cash:", START_CASH)
    print("final_equity:", round(final_eq,2))
    print("trades_total:", len(trades), "sells:", len(sells), "winrate%:", round(winrate,1))
    print("max_drawdown_usd:", round(max_dd,2))
    print("saved:", trades_csv)
    print("saved:", equity_csv)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
