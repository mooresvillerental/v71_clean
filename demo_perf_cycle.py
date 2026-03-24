
import json
import time
from app.ezcore_v1.core.config import CoreConfig
from app.ezcore_v1.core.engine import CoreV1


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


STATE = "app/ezcore_v1_state.json"

def load_state():
    with open(STATE,"r") as f:
        return json.load(f)

def save_state(st):
    with open(STATE,"w") as f:
        json.dump(st,f,indent=2)

def main():

    cfg = CoreConfig()
    bot = CoreV1(cfg)

    symbol = "BTC-USD"

    print("=== FORCED PERF TEST ===")

    st = load_state()

    # simulate entry
    entry_price = 45000.0
    bot._perf_open(
        st,
        symbol,
        entry_price,
        55,
        "TEST_ENTRY",
        ["forced entry"]
    )

    print("opened position at", entry_price)

    time.sleep(2)

    # simulate price movement
    exit_price = 46000.0

    bot._perf_close(
        st,
        symbol,
        exit_price,
        72,
        "TEST_EXIT",
        ["forced exit"]
    )

    save_state(st)

    print("closed position at", exit_price)

    notify_test_complete("EZTRADER test complete")

if __name__ == "__main__":
    main()
