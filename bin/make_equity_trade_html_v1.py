#!/usr/bin/env python3
from pathlib import Path
import csv, math
from datetime import datetime

def latest(globpat):
    files = sorted(Path("backtests").glob(globpat), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None

def read_csv(p):
    with p.open("r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.reader(f)
        rows = list(r)
    if not rows: return [], []
    return rows[0], rows[1:]

def parse_dt(s):
    s = (s or "").strip()
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            pass
    return None

def pick(headers, name):
    name = name.lower()
    for i,h in enumerate(headers):
        if h.lower()==name: return i
    return None

def nearest_idx(times, t):
    # times sorted
    if not times: return None
    lo, hi = 0, len(times)-1
    while lo < hi:
        mid = (lo+hi)//2
        if times[mid] < t: lo = mid+1
        else: hi = mid
    if lo == 0: return 0
    if times[lo] == t: return lo
    return lo if abs((times[lo]-t).total_seconds()) < abs((times[lo-1]-t).total_seconds()) else lo-1

def main():
    eq = latest("equity_90d_*.csv")
    tr = latest("trades_90d_*.csv")
    if not eq or not tr:
        print("Missing backtest CSVs in backtests/")
        return 2

    eh, ed = read_csv(eq)
    th, td = read_csv(tr)

    ti = pick(eh, "utc_time")
    ei = pick(eh, "equity_usd") if pick(eh, "equity_usd") is not None else pick(eh, "equity")
    if ti is None: ti = 0
    if ei is None: ei = 1

    T, Y = [], []
    for row in ed:
        if len(row) <= max(ti, ei): continue
        dt = parse_dt(row[ti]); 
        if not dt: continue
        try: y = float(row[ei])
        except Exception: continue
        T.append(dt); Y.append(y)

    if not T:
        print("No equity rows parsed.")
        return 3

    # sort
    z = sorted(zip(T,Y), key=lambda p:p[0])
    T = [a for a,_ in z]; Y = [b for _,b in z]

    t_ti = pick(th, "utc_time"); 
    t_side = pick(th, "side")
    t_sym  = pick(th, "symbol")
    t_usd  = pick(th, "usd")
    if t_ti is None: t_ti = 0

    trades = []
    for row in td:
        if len(row) <= t_ti: continue
        dt = parse_dt(row[t_ti]); 
        if not dt: continue
        side = (row[t_side] if t_side is not None and t_side < len(row) else "").strip().upper()
        sym  = (row[t_sym]  if t_sym  is not None and t_sym  < len(row) else "").strip().upper()
        usd  = None
        if t_usd is not None and t_usd < len(row):
            try: usd = float(row[t_usd])
            except Exception: usd = None
        trades.append((dt, side, sym, usd))

    # scales
    w, h = 1100, 520
    padL, padR, padT, padB = 60, 20, 20, 50
    x0, x1 = padL, w-padR
    y0, y1 = padT, h-padB

    tmin, tmax = T[0], T[-1]
    ymin, ymax = min(Y), max(Y)
    if abs(ymax-ymin) < 1e-9:
        ymax = ymin + 1.0

    def x(dt):
        frac = (dt - tmin).total_seconds() / max(1.0, (tmax - tmin).total_seconds())
        return x0 + frac*(x1-x0)

    def y(v):
        frac = (v - ymin) / (ymax - ymin)
        return y1 - frac*(y1-y0)

    # polyline points
    pts = " ".join(f"{x(T[i]):.2f},{y(Y[i]):.2f}" for i in range(len(T)))

    # markers
    buys, sells = [], []
    for dt, side, sym, usd in trades:
        idx = nearest_idx(T, dt)
        if idx is None: continue
        mx, my = x(T[idx]), y(Y[idx])
        coin = sym.split("-",1)[0] if sym else ""
        tag = f"{side} {coin}".strip()
        if usd is not None and usd>0: tag += f" ${usd:,.0f}"
        if side == "BUY": buys.append((mx,my,tag))
        elif side == "SELL": sells.append((mx,my,tag))

    out = Path("backtests")/f"equity_with_trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    html = f"""<!doctype html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>EZTrader Backtest — Equity with Trades</title>
<style>
body{{font-family:system-ui,Segoe UI,Roboto,Arial;margin:16px}}
.card{{max-width:{w}px;margin:auto;border:1px solid #ddd;border-radius:12px;padding:12px}}
.small{{opacity:.75;font-size:12px}}
svg{{width:100%;height:auto}}
.tooltip{{position:fixed;left:0;top:0;transform:translate(-9999px,-9999px);
background:#111;color:#fff;padding:6px 8px;border-radius:8px;font-size:12px;pointer-events:none;opacity:.92}}
</style>
<style id="EZ_MOBILE_RESPONSIVE_V1">
  html, body { height: 100%; margin: 0; }
  body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; }
  .wrap { max-width: 980px; margin: 0 auto; padding: 10px; }
  .chartbox { height: min(78vh, 620px); width: 100%; }
  canvas { width: 100% !important; height: 100% !important; }
</style>
</head>

<body>
<div class="card">
  <div><b>EZTrader Backtest (90d)</b> — Equity with Trade Markers</div>
  <div class="small">Equity range: ${ymin:,.2f} → ${ymax:,.2f} | Trades: {len(trades)} | Source: {eq.name}, {tr.name}</div>
  <svg viewBox="0 0 {w} {h}" role="img" aria-label="Equity curve with trade markers">
    <line x1="{x0}" y1="{y0}" x2="{x0}" y2="{y1}" stroke="#888" stroke-width="1"/>
    <line x1="{x0}" y1="{y1}" x2="{x1}" y2="{y1}" stroke="#888" stroke-width="1"/>
    <polyline fill="none" stroke="#000" stroke-width="2" points="{pts}"/>
    <!-- BUY markers -->
    {''.join(f'<circle cx="{mx:.2f}" cy="{my:.2f}" r="6" fill="#2a7" data-tip="{tag}"></circle>' for mx,my,tag in buys)}
    <!-- SELL markers -->
    {''.join(f'<rect x="{mx-6:.2f}" y="{my-6:.2f}" width="12" height="12" fill="#c33" data-tip="{tag}"></rect>' for mx,my,tag in sells)}
  </svg>
  <div class="small">BUY = green circle | SELL = red square (tap/hover to see details)</div>
</div>
<div class="tooltip" id="tt"></div>
<script>
const tt = document.getElementById('tt');
function show(e, text) {{
  tt.textContent = text;
  tt.style.transform = `translate(${e.clientX+12}px, ${e.clientY+12}px)`;
}}
document.addEventListener('mousemove', (e) => {{
  const t = e.target;
  const tip = t && t.getAttribute && t.getAttribute('data-tip');
  if (tip) {{ show(e, tip); }}
  else {{ tt.style.transform = 'translate(-9999px,-9999px)'; }}
}});
document.addEventListener('click', (e) => {{
  const t = e.target;
  const tip = t && t.getAttribute && t.getAttribute('data-tip');
  if (tip) alert(tip);
}});
</script>
</body></html>
"""
    out.write_text(html, encoding="utf-8")
    print(str(out))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
