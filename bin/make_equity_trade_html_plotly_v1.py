#!/usr/bin/env python3
from pathlib import Path
import csv, json, time
from datetime import datetime

def latest(globpat: str) -> Path:
    files = sorted(Path("backtests").glob(globpat), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        raise SystemExit(f"ERROR: no backtests/{globpat} found")
    return files[0]

def parse_dt(s: str) -> datetime | None:
    s = (s or "").strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            pass
    return None

def read_equity(path: Path):
    xs, ys = [], []
    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            dt = parse_dt(row.get("utc_time",""))
            if not dt:
                continue
            try:
                eq = float(row.get("equity_usd",""))
            except Exception:
                continue
            xs.append(dt)
            ys.append(eq)
    if not xs:
        raise SystemExit("ERROR: equity CSV parsed to 0 rows")
    return xs, ys

def read_trades(path: Path):
    out = []
    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            dt = parse_dt(row.get("utc_time",""))
            if not dt:
                continue
            side = (row.get("side","") or "").strip().upper()
            sym  = (row.get("symbol","") or "").strip().upper()
            usd  = row.get("usd","")
            try:
                usd = float(usd) if usd not in (None,"") else None
            except Exception:
                usd = None
            out.append((dt, side, sym, usd))
    return out

def nearest_index(xs, x):
    # xs sorted
    lo, hi = 0, len(xs)-1
    if x <= xs[0]: return 0
    if x >= xs[-1]: return len(xs)-1
    while lo < hi:
        mid = (lo + hi) // 2
        if xs[mid] < x:
            lo = mid + 1
        else:
            hi = mid
    if lo == 0:
        return 0
    # choose closest of lo / lo-1
    a = xs[lo]
    b = xs[lo-1]
    return lo if abs((a-x).total_seconds()) < abs((x-b).total_seconds()) else (lo-1)

def main():
    eqp = latest("equity_90d_*.csv")
    trp = latest("trades_90d_*.csv")

    xs, ys = read_equity(eqp)
    trades = read_trades(trp)

    # ensure sorted
    z = sorted(zip(xs, ys), key=lambda t: t[0])
    xs = [a for a,_ in z]
    ys = [b for _,b in z]

    buy_x, buy_y, buy_t = [], [], []
    sell_x, sell_y, sell_t = [], [], []

    for (dt, side, sym, usd) in trades:
        i = nearest_index(xs, dt)
        x = xs[i].isoformat(sep=" ")
        y = ys[i]
        coin = sym.split("-",1)[0] if sym else ""
        usd_txt = f" ${usd:,.0f}" if isinstance(usd,(int,float)) else ""
        label = f"{side} {coin}{usd_txt}".strip()

        if side == "BUY":
            buy_x.append(x); buy_y.append(y); buy_t.append(label)
        elif side == "SELL":
            sell_x.append(x); sell_y.append(y); sell_t.append(label)

    out = Path("backtests") / f"equity_with_trades_{time.strftime('%Y%m%d_%H%M%S')}.html"

    X = [d.isoformat(sep=" ") for d in xs]
    Y = ys

    html = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>EZTrader Backtest — Equity + Trades</title>
  <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
  <style>
    body {{ margin: 0; font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial; }}
    #chart {{ width: 100vw; height: 100vh; }}
  </style>
</head>
<body>
<div id="chart"></div>
<script>
const equityX = {json.dumps(X)};
const equityY = {json.dumps(Y)};

const buyX = {json.dumps(buy_x)};
const buyY = {json.dumps(buy_y)};
const buyT = {json.dumps(buy_t)};

const sellX = {json.dumps(sell_x)};
const sellY = {json.dumps(sell_y)};
const sellT = {json.dumps(sell_t)};

const traceEquity = {{
  x: equityX, y: equityY,
  mode: 'lines',
  name: 'Equity (USD)',
  hovertemplate: '%{{x}}<br>$%{{y:.2f}}<extra></extra>'
}};

const traceBuy = {{
  x: buyX, y: buyY,
  mode: 'markers',
  name: 'BUY',
  text: buyT,
  hovertemplate: '%{{x}}<br>%{{text}}<br>$%{{y:.2f}}<extra></extra>',
  marker: {{ size: 10, symbol: 'triangle-up' }}
}};

const traceSell = {{
  x: sellX, y: sellY,
  mode: 'markers',
  name: 'SELL',
  text: sellT,
  hovertemplate: '%{{x}}<br>%{{text}}<br>$%{{y:.2f}}<extra></extra>',
  marker: {{ size: 10, symbol: 'triangle-down' }}
}};

Plotly.newPlot('chart', [traceEquity, traceBuy, traceSell], {{
  title: 'EZTrader Backtest (90d) — Equity with BUY/SELL markers',
  xaxis: {{ title: 'UTC Time' }},
  yaxis: {{ title: 'Equity (USD)' }},
  margin: {{ l: 50, r: 20, t: 50, b: 50 }},
}}, {{displayModeBar: true}});
</script>
</body>
</html>
"""
    out.write_text(html, encoding="utf-8")
    print(str(out))

if __name__ == "__main__":
    raise SystemExit(main())
