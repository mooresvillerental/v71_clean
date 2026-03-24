import json
from pathlib import Path
from collections import Counter

path = Path("signals/signal_history.jsonl")

signals = []

with path.open() as f:
    for line in f:
        try:
            signals.append(json.loads(line))
        except:
            pass

actions = Counter()
strategies = Counter()
regimes = Counter()
pairs = Counter()

for s in signals:
    action = s.get("action")
    strategy = s.get("strategy")
    regime = s.get("regime","UNKNOWN")

    actions[action] += 1
    strategies[strategy] += 1
    regimes[regime] += 1
    pairs[(strategy, regime)] += 1

print("\n===== EZTRADER SIGNAL ANALYZER =====")

print("\nSignals analyzed:", len(signals))

print("\nAction distribution")
for k,v in actions.most_common():
    print(k,v)

print("\nStrategy distribution")
for k,v in strategies.most_common():
    print(k,v)

print("\nRegime distribution")
for k,v in regimes.most_common():
    print(k,v)

print("\nStrategy vs Regime")
for (s,r),v in pairs.most_common():
    print(f"{s:15} {r:8} {v}")

print("\n====================================")
