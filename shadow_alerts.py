import json
import os
import time
from pathlib import Path

OPEN_FILE = Path("signals/shadow_trades_open.jsonl")
COUNTER_FILE = Path("signals/shadow_trade_counter.json")
POLL_SECONDS = 3

last_open_count = 0
seen_keys = set()

def speak(text: str):
    os.system(f'termux-tts-speak "{text}"')

def load_counter():
    if not COUNTER_FILE.exists():
        return 0
    try:
        data = json.loads(COUNTER_FILE.read_text(encoding="utf-8"))
        return int(data.get("count", 0))
    except Exception:
        return 0

def save_counter(count: int):
    COUNTER_FILE.write_text(
        json.dumps({"count": count}, indent=2) + "\n",
        encoding="utf-8"
    )

def load_open_rows():
    rows = []
    if not OPEN_FILE.exists():
        return rows
    with OPEN_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    return rows

lifetime_count = load_counter()

print("Watching shadow trades...")

while True:
    try:
        rows = load_open_rows()
        open_count = len(rows)

        current_keys = set()
        new_rows = []

        for r in rows:
            key = (
                str(r.get("opened_timestamp")),
                str(r.get("symbol")),
                str(r.get("action")),
                str(r.get("strategy")),
                str(r.get("entry_price")),
            )
            current_keys.add(key)
            if key not in seen_keys:
                new_rows.append(r)

        # Speak newly opened shadow trades with lifetime numbering
        for _ in new_rows:
            lifetime_count += 1
            save_counter(lifetime_count)
            print(f"SHADOW ALERT: lifetime trade {lifetime_count}")
            speak(f"EZTrader shadow trade {lifetime_count}")

        seen_keys = current_keys
        last_open_count = open_count

    except Exception as e:
        print("Shadow alert error:", e)

    time.sleep(POLL_SECONDS)
