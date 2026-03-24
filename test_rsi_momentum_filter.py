import json

p="app/ezcore_v1_state.json"

try:
    st=json.load(open(p,"r"))
except:
    print("No state file found")
    raise SystemExit

perf=st.get("perf") or {}
trades=perf.get("trades") or []

kept=[]
removed=[]

for t in trades:
    rsi=t.get("entry_rsi")
    if rsi is None:
        kept.append(t)
        continue

    # simulate momentum requirement
    if rsi >= 50:
        kept.append(t)
    else:
        removed.append(t)

print("Original trades:",len(trades))
print("Kept trades:",len(kept))
print("Filtered trades:",len(removed))
