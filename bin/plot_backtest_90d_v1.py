#!/usr/bin/env python3
from pathlib import Path
import csv, sys, math
from datetime import datetime

def _latest(pattern: str) -> Path | None:
    files = sorted(Path("backtests").glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None

def _pick_col(headers, prefers):
    hlow = [h.lower() for h in headers]
    for pref in prefers:
        for i, h in enumerate(hlow):
            if pref in h:
                return i
    return None

def _read_csv(path: Path):
    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        r = csv.reader(f)
        rows = list(r)
    if not rows:
        return [], []
    headers = rows[0]
    data = rows[1:]
    return headers, data

def _to_float(x):
    try:
        return float(x)
    except Exception:
        return None

def _to_int(x):
    try:
        return int(float(x))
    except Exception:
        return None

def _parse_time_val(s):
    s = (s or "").strip()
    if not s:
        return None
    # try epoch seconds/ms
    n = _to_int(s)
    if n is not None:
        # heuristic: ms if very large
        if n > 10_000_000_000:
            return n / 1000.0
        return float(n)
    # try ISO-ish
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.timestamp()
        except Exception:
            pass
    return None

def _nearest_index(xs, x):
    # xs sorted
    if not xs:
        return None
    lo, hi = 0, len(xs) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if xs[mid] < x:
            lo = mid + 1
        else:
            hi = mid
    # lo is first >= x
    if lo == 0:
        return 0
    if xs[lo] == x:
        return lo
    # compare lo vs lo-1
    return lo if abs(xs[lo] - x) < abs(xs[lo-1] - x) else (lo-1)

def main():
    eq = _latest("equity_90d_*.csv")
    tr = _latest("trades_90d_*.csv")

    if not eq:
        print("ERROR: no backtests/equity_90d_*.csv found")
        return 2
    if not tr:
        print("ERROR: no backtests/trades_90d_*.csv found")
        return 2

    eq_h, eq_d = _read_csv(eq)
    tr_h, tr_d = _read_csv(tr)

    # Pick columns robustly
    eq_ti = _pick_col(eq_h, ["ts", "time", "date"])
    eq_ei = _pick_col(eq_h, ["equity", "total", "value", "balance"])

    if eq_ti is None:
        eq_ti = 0
    if eq_ei is None:
        eq_ei = len(eq_h) - 1

    xs, ys = [], []
    for row in eq_d:
        if len(row) <= max(eq_ti, eq_ei):
            continue
        t = _parse_time_val(row[eq_ti])
        y = _to_float(row[eq_ei])
        if t is None or y is None:
            continue
        xs.append(t)
        ys.append(y)

    if not xs:
        print("ERROR: could not parse equity data (no time/equity rows)")
        return 3

    # Ensure sorted by time
    zipped = sorted(zip(xs, ys), key=lambda p: p[0])
    xs = [a for a, _ in zipped]
    ys = [b for _, b in zipped]

    tr_ti = _pick_col(tr_h, ["ts", "time", "date"])
    tr_side_i = _pick_col(tr_h, ["side", "action", "type"])
    tr_sym_i = _pick_col(tr_h, ["symbol", "sym", "asset"])
    tr_price_i = _pick_col(tr_h, ["price"])
    tr_usd_i = _pick_col(tr_h, ["usd", "notional", "amount", "value"])

    if tr_ti is None:
        tr_ti = 0

    trades = []
    for row in tr_d:
        if len(row) <= tr_ti:
            continue
        t = _parse_time_val(row[tr_ti])
        if t is None:
            continue
        side = (row[tr_side_i] if (tr_side_i is not None and tr_side_i < len(row)) else "").strip().upper()
        sym  = (row[tr_sym_i]  if (tr_sym_i  is not None and tr_sym_i  < len(row)) else "").strip().upper()
        px   = _to_float(row[tr_price_i]) if (tr_price_i is not None and tr_price_i < len(row)) else None
        usd  = _to_float(row[tr_usd_i])   if (tr_usd_i   is not None and tr_usd_i   < len(row)) else None
        trades.append((t, side, sym, px, usd))

    # Plot
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out = Path("backtests") / f"equity_with_trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"

    fig = plt.figure(figsize=(11, 6))
    ax = fig.add_subplot(111)

    # Convert to datetime for x-axis labels
    xdt = [datetime.fromtimestamp(t) for t in xs]
    ax.plot(xdt, ys, linewidth=2)

    # Mark trades on the equity curve
    buy_x, buy_y, sell_x, sell_y = [], [], [], []
    for (t, side, sym, px, usd) in trades:
        idx = _nearest_index(xs, t)
        if idx is None:
            continue
        tx = datetime.fromtimestamp(xs[idx])
        ty = ys[idx]
        label = side or "TRADE"
        if sym:
            label += f" {sym.split('-')[0]}"
        if usd is not None and usd > 0:
            label += f" ${usd:,.0f}"
        if side == "BUY":
            buy_x.append(tx); buy_y.append(ty)
            ax.annotate("BUY", (tx, ty), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=8)
        elif side == "SELL":
            sell_x.append(tx); sell_y.append(ty)
            ax.annotate("SELL", (tx, ty), textcoords="offset points", xytext=(0, -12), ha="center", fontsize=8)
        else:
            ax.annotate("TRADE", (tx, ty), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=8)

    if buy_x:
        ax.scatter(buy_x, buy_y, marker="^", s=60)
    if sell_x:
        ax.scatter(sell_x, sell_y, marker="v", s=60)

    ax.set_title("EZTrader Backtest (90d) — Equity with Trade Markers")
    ax.set_xlabel("Time")
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
