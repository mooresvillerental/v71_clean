
import json
import subprocess
import os


import shutil
import subprocess


def _silence_trade_alerts(bot):
    try:
        if hasattr(bot, "alerts") and hasattr(bot.alerts, "announce"):
            bot.alerts.announce = lambda msg: None
    except Exception:
        pass


def notify_test_complete(msg="EZTRADER test complete"):
    try:
        if shutil.which("termux-tts-speak"):
            subprocess.run(["termux-tts-speak", msg], check=False)
        else:
            print(msg)
    except Exception:
        print(msg)


KNOBS_FILE = "logs/ezcore_v1_knobs.json"
STATE_FILE = "app/ezcore_v1_state.json"

RSI_VALUES = [65,70,75,80,90]
CONFIRM_VALUES = [1,2,3]

START_EQUITY = 100.0

def run_demo():

    subprocess.run(
        "rm -f app/ezcore_v1_state.json logs/ezcore_v1.log logs/ezcore_v1_events.jsonl",
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    subprocess.run(
        "python -u -m app.ezcore_v1.demo_run",
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

def read_results():

    st = json.load(open(STATE_FILE))
    perf = st.get("perf") or {}
    trades = perf.get("trades") or []
    open_pos = perf.get("open_pos")

    wins = [t for t in trades if (t.get("pnl_pct") or 0) > 0]
    losses = [t for t in trades if (t.get("pnl_pct") or 0) <= 0]

    pnl_total = sum((t.get("pnl_pct") or 0) for t in trades)

    equity = START_EQUITY
    for t in trades:
        p = t.get("pnl_pct") or 0
        equity *= (1 + p/100)

    winrate = 0
    if trades:
        winrate = len(wins)/len(trades)*100

    buy_rows = st.get("seen_signals_log",[])
    buy_rows = [r for r in buy_rows if r.get("action")=="BUY"]

    attempts = st.get("stats",{}).get("buy_attempts_B",0)

    return {
        "trades": len(trades),
        "winrate": round(winrate,1),
        "pnl_pct": round(pnl_total,3),
        "ending_equity": round(equity,3),
        "buy_rows": len(buy_rows),
        "buy_attempts": attempts,
        "open_pos": 1 if open_pos else 0
    }

def set_knobs(rsi,confirm):

    k = {}
    if os.path.exists(KNOBS_FILE):
        k=json.load(open(KNOBS_FILE))

    k["EZ_BUY_RSI_MAX"]=rsi
    k["EZ_BUY_CONFIRM_BARS"]=confirm

    json.dump(k,open(KNOBS_FILE,"w"),indent=2)

def main():

    results=[]

    print("\n=== KNOB SWEEP ===\n")

    for rsi in RSI_VALUES:
        for confirm in CONFIRM_VALUES:

            set_knobs(rsi,confirm)

            run_demo()

            perf = read_results()

            row = {
                "rsi":rsi,
                "confirm":confirm,
                **perf
            }

            results.append(row)

            print(row)

    print("\n=== BEST BY EQUITY ===\n")

    best=max(results,key=lambda x:x["ending_equity"])

    print(best)

    notify_test_complete("EZTRADER test complete")

if __name__=="__main__":
    main()
