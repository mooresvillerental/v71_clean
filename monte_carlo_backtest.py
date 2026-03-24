
import subprocess
import json
import random
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


STATE_FILE="app/ezcore_v1_state.json"

RUNS=50

def reset_state():
    subprocess.run(
        "rm -f app/ezcore_v1_state.json logs/ezcore_v1.log logs/ezcore_v1_events.jsonl",
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

def run_test():
    subprocess.run(
        "python backtest_long_run.py",
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    st=json.load(open(STATE_FILE,"r",encoding="utf-8"))
    perf=st.get("perf") or {}
    trades=perf.get("trades") or []

    equity=100.0

    for t in trades:
        pnl=t.get("pnl_pct")
        if pnl is None:
            continue
        equity*=1+(pnl/100)

    return equity


results=[]

print("=== MONTE CARLO TEST ===")

for i in range(RUNS):

    reset_state()
    run_test()

    eq=run_test()

    results.append(eq)

    print("run",i+1,"ending_equity",round(eq,3))


avg=sum(results)/len(results)

best=max(results)
worst=min(results)

sorted_res=sorted(results)
median=sorted_res[len(results)//2]

print()
print("=== MONTE CARLO SUMMARY ===")
print("runs:",RUNS)
print("avg_equity:",round(avg,3))
print("median_equity:",round(median,3))
print("best_equity:",round(best,3))
print("worst_equity:",round(worst,3))
notify_test_complete("EZTRADER test complete")
