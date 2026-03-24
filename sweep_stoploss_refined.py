
import json
import subprocess
import os

STATE_FILE = "app/ezcore_v1_state.json"
KNOBS_FILE = "logs/ezcore_v1_knobs.json"

STOP_VALUES = [1.2,1.4,1.5,1.6,1.8]
START_EQUITY = 100.0

def set_stoploss(v):
    k={}
    if os.path.exists(KNOBS_FILE):
        k=json.load(open(KNOBS_FILE))
    k["EZ_PAPER_STOP_LOSS_PCT"]=float(v)
    json.dump(k,open(KNOBS_FILE,"w"),indent=2)

def run_backtest():
    subprocess.run(
        "rm -f app/ezcore_v1_state.json logs/ezcore_v1.log logs/ezcore_v1_events.jsonl",
        shell=True
    )

    subprocess.run(
        "EZ_SILENT_TESTS=1 python backtest_long_run.py",
        shell=True
    )

def read_equity():

    st=json.load(open(STATE_FILE))
    perf=st.get("perf") or {}
    trades=perf.get("trades") or []

    equity=START_EQUITY

    for t in trades:
        pnl=t.get("pnl_pct")
        if pnl is None:
            continue
        equity*=1+(pnl/100)

    return equity,len(trades)

results=[]

print("=== REFINED STOP SWEEP ===")

for stop in STOP_VALUES:

    set_stoploss(stop)
    run_backtest()

    eq,trades=read_equity()

    row={
        "stop":stop,
        "ending_equity":round(eq,3),
        "trades":trades
    }

    results.append(row)
    print(row)

print()
print("=== BEST STOP ===")

best=max(results,key=lambda x:x["ending_equity"])
print(best)
