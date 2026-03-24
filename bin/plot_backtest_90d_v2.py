#!/usr/bin/env python3
from pathlib import Path
import csv
from datetime import datetime

def latest(pattern: str) -> Path:
    files = sorted(Path("backtests").glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        raise SystemExit(f"ERROR: no backtests/{pattern} found")
    return files[0]

def parse_dt(s: str):
    s = (s or "").strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            pass
    return None

def to_float(x):
    try:
        return float(x)
    except Exception:
        return None

def read_csv(path: Path):
    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.reader(f)
        rows = list(r)
    if not rows:
        return [], []
    return rows[0], rows[1:]

def col_idx(headers, name):
    h = [x.strip().lower() for x in headers]
    name = name.lower()
    for i, v in enumerate(h):
        if v == name:
            return i
    return None

def nearest_index(xs, x):
    # xs sorted list of datetimes
    if not xs:
        return None
    lo, hi = 0, len(xs)-1
    while lo < hi:
        mid = (lo+hi)//2
        if xs[mid] < x:
            lo = mid + 1
        else:
            hi = mid
    if lo == 0:
        return 0
    if xs[lo] == x:
        return lo
    return lo if abs((xs[lo]-x).total_seconds()) < abs((xs[lo-1]-x).total_seconds()) else (lo-1)

def main():
    eq_path = latest("equity_90d_*.csv")
    tr_path = latest("trades_90d_*.csv")

    eq_h, eq_d = read_csv(eq_path)
    tr_h, tr_d = read_csv(tr_path)

    eq_ti = col_idx(eq_h, "utc_time")
    eq_ei = col_idx(eq_h, "equity_usd")
    if eq_ti is None or eq_ei is None:
        raise SystemExit(f"ERROR: equity csv missing utc_time/equity_usd headers: {eq_h}")

    xs, ys = [], []
    for row in eq_d:
        if len(row) <= max(eq_ti, eq_ei):
            continue
        dt = parse_dt(row[eq_ti])
        y = to_float(row[eq_ei])
        if dt is None or y is None:
            continue
        xs.append(dt); ys.append(y)

    if not xs:
        raise SystemExit("ERROR: parsed 0 equity points")

    # sort + de-dupe consecutive duplicates (keeps plot cleaner)
    pts = sorted(zip(xs, ys), key=lambda p: p[0])
    xs, ys = [], []
    last = None
    for dt, y in pts:
        if last and dt == last[0] and y == last[1]:
            continue
        xs.append(dt); ys.append(y)
        last = (dt, y)

    tr_ti   = col_idx(tr_h, "utc_time")
    tr_side = col_idx(tr_h, "side")
    tr_sym  = col_idx(tr_h, "symbol")
    tr_usd  = col_idx(tr_h, "usd")

    if tr_ti is None or tr_side is None:
        raise SystemExit(f"ERROR: trades csv missing utc_time/side headers: {tr_h}")

    trades = []
    for row in tr_d:
        if len(row) <= tr_ti:
            continue
        dt = parse_dt(row[tr_ti])
        if dt is None:
            continue
        side = (row[tr_side] if tr_side is not None and tr_side < len(row) else "").strip().upper()
        sym  = (row[tr_sym]  if tr_sym  is not None and tr_sym  < len(row) else "").strip().upper()
        usd  = to_float(row[tr_usd]) if (tr_usd is not None and tr_usd < len(row)) else None
        trades.append((dt, side, sym, usd))

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out = Path("backtests") / f"equity_with_trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"

    fig = plt.figure(figsize=(11,6))
    ax = fig.add_subplot(111)
    ax.plot(xs, ys, linewidth=2)

    buy_x, buy_y, sell_x, sell_y = [], [], [], []
    for dt, side, sym, usd in trades:
        idx = nearest_index(xs, dt)
        if idx is None:
            continue
        tx, ty = xs[idx], ys[idx]
        coin = (sym.split("-",1)[0] if sym else "").strip()
        amt = (f" ${usd:,.0f}" if usd is not None and usd > 0 else "")
        if side == "BUY":
            buy_x.append(tx); buy_y.append(ty)
            ax.annotate(f"BUY {coin}{amt}".strip(), (tx, ty), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=8)
        elif side == "SELL":
            sell_x.append(tx); sell_y.append(ty)
            ax.annotate(f"SELL {coin}{amt}".strip(), (tx, ty), textcoords="offset points", xytext=(0, -12), ha="center", fontsize=8)

    if buy_x:
        ax.scatter(buy_x, buy_y, marker="^", s=60)
    if sell_x:
        ax.scatter(sell_x, sell_y, marker="v", s=60)

    ax.set_title("EZTrader Backtest (90d) — Equity with BUY/SELL Markers")
    ax.set_xlabel("Time (UTC)")
    ax.set_ylabel("Equity (USD)")
    ax.grid(True, alpha=0.25)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(out, dpi=160)
    plt.close(fig)

    print(str(out))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
