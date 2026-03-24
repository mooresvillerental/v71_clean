#!/usr/bin/env python3
import json
from pathlib import Path

STATE_PATH = Path("app/ezcore_v1_state.json")
START_EQUITY = 100.0

def main():
    if not STATE_PATH.exists():
        print("Missing state file:", STATE_PATH)
        return

    st = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    perf = st.get("perf") or {}
    trades = perf.get("trades") or []
    open_pos = perf.get("open_pos")

    print("=== PERF ANALYTICS ===")
    print("trades:", len(trades))
    print("open_pos_count:", 1 if open_pos else 0)

    if not trades:
        print("wins: 0  losses: 0  winrate: 0.0%")
        print("avg_win_pct: 0.000%  avg_loss_pct: 0.000%")
        print("expectancy_pct: 0.000%")
        print("profit_factor: n/a")
        print("cumulative_pnl_pct: 0.000%")
        print("avg_hold_s: 0")
        print("starting_equity:", f"{START_EQUITY:.3f}")
        print("ending_equity:", f"{START_EQUITY:.3f}")
        print("max_drawdown_pct: 0.000%")
        print("best_streak: 0")
        print("worst_streak: 0")
        print("best_trade: none")
        print("worst_trade: none")
        if open_pos:
            print("open_pos:", open_pos)
        return

    def pnl(t):
        v = t.get("pnl_pct")
        return None if v is None else float(v)

    closed = [t for t in trades if pnl(t) is not None]
    wins = [t for t in closed if pnl(t) > 0]
    losses = [t for t in closed if pnl(t) <= 0]

    avg_win = sum(pnl(t) for t in wins) / len(wins) if wins else 0.0
    avg_loss = sum(pnl(t) for t in losses) / len(losses) if losses else 0.0
    winrate = (len(wins) / len(closed) * 100.0) if closed else 0.0
    expectancy = (winrate / 100.0) * avg_win + (1.0 - winrate / 100.0) * avg_loss
    avg_hold = sum(int(t.get("hold_s") or 0) for t in closed) / len(closed) if closed else 0.0

    gross_profit = sum(pnl(t) for t in wins) if wins else 0.0
    gross_loss_abs = abs(sum(pnl(t) for t in losses if pnl(t) < 0)) if losses else 0.0
    profit_factor = (gross_profit / gross_loss_abs) if gross_loss_abs > 0 else None

    cumulative_pnl = sum(pnl(t) for t in closed) if closed else 0.0

    best = max(closed, key=lambda t: pnl(t)) if closed else None
    worst = min(closed, key=lambda t: pnl(t)) if closed else None

    # Equity curve / drawdown
    equity = START_EQUITY
    peak = START_EQUITY
    max_drawdown = 0.0

    best_streak = 0
    worst_streak = 0
    cur_win_streak = 0
    cur_loss_streak = 0

    for t in closed:
        p = pnl(t) or 0.0
        equity *= (1.0 + p / 100.0)

        if equity > peak:
            peak = equity

        if peak > 0:
            dd = (peak - equity) / peak * 100.0
            if dd > max_drawdown:
                max_drawdown = dd

        if p > 0:
            cur_win_streak += 1
            cur_loss_streak = 0
        elif p < 0:
            cur_loss_streak += 1
            cur_win_streak = 0
        else:
            cur_win_streak = 0
            cur_loss_streak = 0

        if cur_win_streak > best_streak:
            best_streak = cur_win_streak
        if cur_loss_streak > worst_streak:
            worst_streak = cur_loss_streak

    print(f"wins: {len(wins)}  losses: {len(losses)}  winrate: {winrate:.1f}%")
    print(f"avg_win_pct: {avg_win:.3f}%  avg_loss_pct: {avg_loss:.3f}%")
    print(f"expectancy_pct: {expectancy:.3f}%")
    print("profit_factor:", "n/a" if profit_factor is None else f"{profit_factor:.3f}")
    print(f"cumulative_pnl_pct: {cumulative_pnl:.3f}%")
    print(f"avg_hold_s: {avg_hold:.1f}")
    print("starting_equity:", f"{START_EQUITY:.3f}")
    print("ending_equity:", f"{equity:.3f}")
    print(f"max_drawdown_pct: {max_drawdown:.3f}%")
    print("best_streak:", best_streak)
    print("worst_streak:", worst_streak)

    if best:
        print("best_trade:", {
            "symbol": best.get("symbol"),
            "pnl_pct": round(pnl(best), 3),
            "entry_strategy": best.get("entry_strategy"),
            "exit_strategy": best.get("exit_strategy"),
            "hold_s": best.get("hold_s"),
        })
    else:
        print("best_trade: none")

    if worst:
        print("worst_trade:", {
            "symbol": worst.get("symbol"),
            "pnl_pct": round(pnl(worst), 3),
            "entry_strategy": worst.get("entry_strategy"),
            "exit_strategy": worst.get("exit_strategy"),
            "hold_s": worst.get("hold_s"),
        })
    else:
        print("worst_trade: none")

    if open_pos:
        print("open_pos:", open_pos)

if __name__ == "__main__":
    main()
