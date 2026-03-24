import json
from pathlib import Path
from collections import Counter
from statistics import mean
import time

LOG = Path("signals/signal_history.jsonl")

if not LOG.exists():
    print("signal_history.jsonl not found")
    exit()

signals = []

with LOG.open() as f:
    for line in f:
        try:
            signals.append(json.loads(line))
        except:
            pass

actions = Counter()
strategies = Counter()
regimes = Counter()
confidence = []
blocked = 0

for s in signals:
    actions[s.get("action")] += 1
    strategies[s.get("strategy")] += 1
    regimes[s.get("regime","UNKNOWN")] += 1
    confidence.append(s.get("confidence",0))

    if s.get("quality_blocked"):
        blocked += 1

print("\n===== EZTRADER ENGINE HEALTH =====")

print("\nTotal signals:", len(signals))

print("\nAction distribution")
for k,v in actions.most_common():
    print(f"{k:6} {v}")

print("\nStrategy distribution")
for k,v in strategies.most_common():
    print(f"{k:20} {v}")

print("\nRegime distribution")
for k,v in regimes.most_common():
    print(f"{k:10} {v}")

print("\nAverage confidence:", round(mean(confidence),2))
print("Confidence gate blocks:", blocked)

recent = signals[-10:]

print("\nLast 10 signals")
for s in recent:
    print(
        time.strftime("%H:%M:%S", time.localtime(s["timestamp"])),
        s.get("strategy"),
        s.get("action"),
        s.get("regime"),
        s.get("confidence")
    )

print("\n===================================")
