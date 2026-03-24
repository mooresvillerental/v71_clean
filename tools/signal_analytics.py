#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

STATE_PATH = Path("app/ezcore_v1_state.json")

# Each tick in demo_run corresponds to a new 15m bar.
HORIZONS = [
    ("15m", 1),
    ("1h", 4),
    ("4h", 16),
]

def safe_float(x):
    try:
        return float(x)
    except Exception:
        return None

def load_seen_log(state_path: Path):
    if not state_path.exists():
        raise SystemExit(f"Missing state file: {state_path}")
    st = json.loads(state_path.read_text(encoding="utf-8", errors="ignore"))
    log = st.get("seen_signals_log") or []
    # keep only items that have a usable price
    cleaned = []
    for r in log:
        if not isinstance(r, dict):
            continue
        px = safe_float(r.get("price"))
        if px is None or px <= 0:
            continue
        cleaned.append({**r, "price": px})
    return cleaned

def pct(a, b):
    # percent change from a -> b
    return ((b - a) / a) * 100.0

def main():
    log = load_seen_log(STATE_PATH)
    if len(log) < 30:
        raise SystemExit(f"Not enough seen_signals_log rows to analyze (got {len(log)}). Run demo_run a couple times first.")

    # stats[strategy][action][horizon] -> counters
    stats = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: {
        "n": 0,
        "wins": 0,
        "avg_move_pct": 0.0,
        "avg_abs_move_pct": 0.0,
    })))

    # We'll score BUY as "win if forward return > 0"
    # We'll score SELL as "win if forward return < 0" (i.e., price went down after SELL)
    for i, r in enumerate(log):
        action = (r.get("action") or "NONE").upper()
        strategy = (r.get("strategy") or "UNKNOWN")
        p0 = r["price"]

        for hname, steps in HORIZONS:
            j = i + steps
            if j >= len(log):
                continue
            p1 = log[j]["price"]
            move = pct(p0, p1)

            bucket = stats[strategy][action][hname]
            bucket["n"] += 1
            bucket["avg_move_pct"] += move
            bucket["avg_abs_move_pct"] += abs(move)

            if action == "BUY" and move > 0:
                bucket["wins"] += 1
            elif action == "SELL" and move < 0:
                bucket["wins"] += 1
            # NONE/HOLD still tracked but "wins" stays 0 by definition

    # finalize averages
    for strat in list(stats.keys()):
        for act in list(stats[strat].keys()):
            for hname in list(stats[strat][act].keys()):
                b = stats[strat][act][hname]
                n = b["n"] or 1
                b["avg_move_pct"] /= n
                b["avg_abs_move_pct"] /= n
                b["win_pct"] = (b["wins"] / n) * 100.0

    # pretty print: only BUY/SELL by default, but keep NONE too (useful)
    def row(strat, act, hname, b):
        return (
            f"{strat:18}  {act:5}  {hname:3}  "
            f"n={b['n']:4d}  win%={b['win_pct']:6.1f}  "
            f"avg={b['avg_move_pct']:7.3f}%  absavg={b['avg_abs_move_pct']:7.3f}%"
        )

    print("\n=== Signal Analytics (from seen_signals_log) ===")
    print(f"Rows analyzed: {len(log)}")
    print("Horizons:", ", ".join([f"{n}({s})" for n,s in HORIZONS]))
    print("\n--- BUY/SELL performance by strategy ---")

    lines = []
    for strat in sorted(stats.keys()):
        for act in ("BUY", "SELL"):
            if act not in stats[strat]:
                continue
            for hname, _ in HORIZONS:
                if hname in stats[strat][act]:
                    lines.append(row(strat, act, hname, stats[strat][act][hname]))

    if not lines:
        print("No BUY/SELL rows found in log yet. Run demo_run until you see alerts, then re-run this script.")
    else:
        for ln in lines:
            print(ln)

    # write machine-readable report
    out = Path("logs/ezcore_v1_signal_analytics.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(stats, indent=2, sort_keys=True), encoding="utf-8")
    print(f"\nWrote: {out}")

if __name__ == "__main__":
    main()
