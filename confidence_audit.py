#!/usr/bin/env python3
import json
from pathlib import Path

STATE_PATH = Path("app/ezcore_v1_state.json")

def score_trade(t):
    score = 0

    strat = str(t.get("entry_strategy") or "").upper()
    exit_strat = str(t.get("exit_strategy") or "").upper()
    pnl = t.get("pnl_pct")
    hold_s = int(t.get("hold_s") or 0)

    # Strategy-based points
    if "TREND" in strat:
        score += 30
    if "BREAKOUT" in strat:
        score += 25

    # Exit behavior clues
    if exit_strat == "ATR_TP":
        score += 15
    elif exit_strat == "EXIT":
        score += 10
    elif exit_strat == "STOPLOSS":
        score -= 10
    elif exit_strat == "TREND_FAIL":
        score -= 15
    elif exit_strat == "RSI_ROLL":
        score += 5

    # Outcome-based points
    try:
        if pnl is not None:
            pnl = float(pnl)
            if pnl >= 1.0:
                score += 25
            elif pnl >= 0.5:
                score += 18
            elif pnl > 0:
                score += 10
            elif pnl > -0.5:
                score -= 5
            elif pnl > -1.5:
                score -= 15
            else:
                score -= 25
    except Exception:
        pass

    # Hold time clue (still weak because current backtests use near-zero real seconds)
    if hold_s >= 60:
        score += 5

    if score < 0:
        score = 0
    if score > 100:
        score = 100

    return int(score)

def bucket_name(s):
    if s >= 85:
        return "ELITE"
    if s >= 70:
        return "STRONG"
    if s >= 55:
        return "GOOD"
    if s >= 40:
        return "WEAK"
    return "POOR"

def main():
    if not STATE_PATH.exists():
        print("Missing state file:", STATE_PATH)
        return

    st = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    perf = st.get("perf") or {}
    trades = perf.get("trades") or []

    print("=== CONFIDENCE AUDIT ===")
    print("trades:", len(trades))

    if not trades:
        print("No trades found.")
        return

    scored = []
    for t in trades:
        s = score_trade(t)
        row = {
            "entry_strategy": t.get("entry_strategy"),
            "exit_strategy": t.get("exit_strategy"),
            "pnl_pct": t.get("pnl_pct"),
            "hold_s": t.get("hold_s"),
            "confidence_score": s,
            "bucket": bucket_name(s),
        }
        scored.append(row)

    # summary by bucket
    buckets = {}
    for row in scored:
        b = row["bucket"]
        buckets.setdefault(b, []).append(row)

    print("\n=== BUCKET SUMMARY ===")
    for b in ["ELITE", "STRONG", "GOOD", "WEAK", "POOR"]:
        rows = buckets.get(b, [])
        if not rows:
            print(b, "count=0")
            continue

        pnls = [float(r["pnl_pct"] or 0.0) for r in rows]
        wins = sum(1 for x in pnls if x > 0)
        losses = sum(1 for x in pnls if x <= 0)
        avg_pnl = sum(pnls) / len(pnls)

        print(
            f"{b} count={len(rows)} wins={wins} losses={losses} "
            f"winrate={wins/len(rows)*100:.1f}% avg_pnl={avg_pnl:.3f}%"
        )

    print("\n=== LAST 15 SCORED TRADES ===")
    for row in scored[-15:]:
        print(row)

if __name__ == "__main__":
    main()
