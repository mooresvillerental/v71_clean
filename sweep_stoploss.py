import json
import subprocess
import os


import shutil
import subprocess

def notify_test_complete(msg="EZTRADER test complete"):
    try:
        if shutil.which("termux-tts-speak"):
            subprocess.run(["termux-tts-speak", msg], check=False)
        else:
            print(msg)
    except Exception:
        print(msg)



def _silence_trade_alerts(bot):
    try:
        if hasattr(bot, "alerts") and hasattr(bot.alerts, "announce"):
            bot.alerts.announce = lambda msg: None
    except Exception:
        pass


STATE_FILE = "app/ezcore_v1_state.json"
KNOBS_FILE = "logs/ezcore_v1_knobs.json"

STOP_VALUES = [1.5, 2.0, 2.5, 3.0]
START_EQUITY = 100.0

def set_stoploss(v):
    k = {}
    if os.path.exists(KNOBS_FILE):
        k = json.load(open(KNOBS_FILE, "r", encoding="utf-8"))
    k["EZ_PAPER_STOP_LOSS_PCT"] = float(v)
    json.dump(k, open(KNOBS_FILE, "w", encoding="utf-8"), indent=2)

def run_backtest():
    subprocess.run(
        "rm -f app/ezcore_v1_state.json logs/ezcore_v1.log logs/ezcore_v1_events.jsonl",
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    subprocess.run(
        "python backtest_long_run.py",
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

def read_stats():
    st = json.load(open(STATE_FILE, "r", encoding="utf-8"))
    perf = st.get("perf") or {}
    trades = perf.get("trades") or []
    open_pos = perf.get("open_pos")

    def pnl(t):
        v = t.get("pnl_pct")
        return None if v is None else float(v)

    closed = [t for t in trades if pnl(t) is not None]
    wins = [t for t in closed if pnl(t) > 0]
    losses = [t for t in closed if pnl(t) <= 0]

    winrate = (len(wins) / len(closed) * 100.0) if closed else 0.0

    gross_profit = sum(pnl(t) for t in wins) if wins else 0.0
    gross_loss_abs = abs(sum(pnl(t) for t in losses if pnl(t) < 0)) if losses else 0.0
    profit_factor = (gross_profit / gross_loss_abs) if gross_loss_abs > 0 else None

    equity = START_EQUITY
    peak = START_EQUITY
    max_drawdown = 0.0
    for t in closed:
        p = pnl(t) or 0.0
        equity *= (1.0 + p / 100.0)
        if equity > peak:
            peak = equity
        if peak > 0:
            dd = (peak - equity) / peak * 100.0
            if dd > max_drawdown:
                max_drawdown = dd

    worst_trade = min((pnl(t) for t in closed), default=None)

    return {
        "trades": len(closed),
        "winrate": round(winrate, 1),
        "ending_equity": round(equity, 3),
        "profit_factor": None if profit_factor is None else round(profit_factor, 3),
        "max_drawdown_pct": round(max_drawdown, 3),
        "worst_trade_pct": None if worst_trade is None else round(worst_trade, 3),
        "open_pos": 1 if open_pos else 0,
    }

def main():
    results = []
    print("=== STOP-LOSS SWEEP ===")
    for stop in STOP_VALUES:
        set_stoploss(stop)
        run_backtest()
        row = {"stop_loss_pct": stop, **read_stats()}
        results.append(row)
        print(row)

    print("\n=== BEST BY ENDING EQUITY ===")
    best = max(results, key=lambda x: x["ending_equity"])
    print(best)

    notify_test_complete("EZTRADER test complete")

if __name__ == "__main__":
    main()
