#!/usr/bin/env python3
from pathlib import Path
import csv, json
from datetime import datetime

def latest(pattern: str):
    files = sorted(Path("backtests").glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None

def read_csv(path: Path):
    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.reader(f)
        rows = list(r)
    if not rows:
        return [], []
    return rows[0], rows[1:]

def main():
    eq = latest("equity_90d_*.csv")
    tr = latest("trades_90d_*.csv")
    if not eq or not tr:
        raise SystemExit("Missing backtest CSVs in backtests/")

    eq_h, eq_d = read_csv(eq)
    tr_h, tr_d = read_csv(tr)

    # expected headers (from your sample):
    # equity: utc_time,equity_usd
    # trades: utc_time,symbol,side,price,qty,usd,rsi,pnl_usd
    eq_time_i = eq_h.index("utc_time") if "utc_time" in eq_h else 0
    eq_val_i  = eq_h.index("equity_usd") if "equity_usd" in eq_h else (len(eq_h)-1)

    labels = []
    equity = []
    for row in eq_d:
        if len(row) <= max(eq_time_i, eq_val_i): 
            continue
        t = row[eq_time_i].strip()
        try:
            y = float(row[eq_val_i])
        except Exception:
            continue
        labels.append(t)
        equity.append(y)

    tr_time_i = tr_h.index("utc_time") if "utc_time" in tr_h else 0
    tr_sym_i  = tr_h.index("symbol") if "symbol" in tr_h else None
    tr_side_i = tr_h.index("side") if "side" in tr_h else None
    tr_usd_i  = tr_h.index("usd") if "usd" in tr_h else None

    # Map trade times to nearest equity index (equity times are already in order)
    idx_by_time = {t:i for i,t in enumerate(labels)}  # exact matches often exist
    buy_pts = []
    sell_pts = []
    for row in tr_d:
        if len(row) <= tr_time_i: 
            continue
        t = row[tr_time_i].strip()
        side = (row[tr_side_i].strip().upper() if tr_side_i is not None and tr_side_i < len(row) else "")
        sym  = (row[tr_sym_i].strip().upper() if tr_sym_i is not None and tr_sym_i < len(row) else "")
        usd  = None
        if tr_usd_i is not None and tr_usd_i < len(row):
            try: usd = float(row[tr_usd_i])
            except Exception: usd = None

        i = idx_by_time.get(t)
        if i is None:
            continue  # keep it simple for now (your files have exact matches)
        coin = sym.split("-",1)[0] if sym else ""
        label = f"{side} {coin}".strip()
        if usd is not None:
            label += f" ${usd:,.0f}"
        pt = {"x": i, "y": equity[i], "label": label}
        if side == "BUY":
            buy_pts.append(pt)
        elif side == "SELL":
            sell_pts.append(pt)

    out = Path("backtests") / f"equity_with_trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"

    html = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>EZTrader Backtest (90d) — Equity + Trades</title>
  <style>
    body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 12px; }}
    .card {{ border: 1px solid #ddd; border-radius: 12px; padding: 12px; }}
    .meta {{ font-size: 14px; opacity: 0.85; margin-bottom: 8px; }}
    canvas {{ width: 100% !important; height: 70vh !important; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="meta">
      <b>EZTrader Backtest (90d)</b> — Equity curve with BUY/SELL markers<br/>
      Equity file: {eq.name}<br/>
      Trades file: {tr.name}
    </div>
    <canvas id="c"></canvas>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
  <script>
    const labels = {json.dumps(labels)};
    const equity = {json.dumps(equity)};
    const buyPts = {json.dumps(buy_pts)};
    const sellPts = {json.dumps(sell_pts)};

    const ctx = document.getElementById('c').getContext('2d');

    const data = {{
      labels,
      datasets: [
        {{
          type: 'line',
          label: 'Equity (USD)',
          data: equity,
          pointRadius: 0,
          borderWidth: 2,
          tension: 0.15
        }},
        {{
          type: 'scatter',
          label: 'BUY',
          data: buyPts.map(p => ({{x: p.x, y: p.y, label: p.label}})),
          pointRadius: 6,
          pointHoverRadius: 8,
        }},
        {{
          type: 'scatter',
          label: 'SELL',
          data: sellPts.map(p => ({{x: p.x, y: p.y, label: p.label}})),
          pointRadius: 6,
          pointHoverRadius: 8,
        }},
      ]
    }};

    const chart = new Chart(ctx, {{
      data,
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        scales: {{
          x: {{
            ticks: {{
              maxTicksLimit: 10,
              callback: (val) => labels[val] || ''
            }}
          }},
          y: {{
            title: {{ display: true, text: 'USD' }}
          }}
        }},
        plugins: {{
          tooltip: {{
            callbacks: {{
              title: (items) => {{
                const i = items?.[0]?.dataIndex;
                return labels[i] || '';
              }},
              label: (item) => {{
                const dsLabel = item.dataset.label || '';
                const raw = item.raw || {{}};
                if (dsLabel === 'Equity (USD)') {{
                  return `Equity: $${{Number(raw).toFixed(2)}}`;
                }}
                if (raw.label) return raw.label;
                return dsLabel;
              }}
            }}
          }}
        }}
      }}
    }});
  </script>
</body>
</html>
"""
    out.write_text(html, encoding="utf-8")
    print(str(out))

if __name__ == "__main__":
    main()
