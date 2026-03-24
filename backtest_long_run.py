import random
import json
import subprocess
from app.ezcore_v1.core.config import CoreConfig
from app.ezcore_v1.core.engine import CoreV1


import shutil
import subprocess


def _silence_trade_recommendations(bot):
    try:
        if hasattr(bot, "announce_signal"):
            bot.announce_signal = lambda *args, **kwargs: None
    except Exception:
        pass



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


STATE = "app/ezcore_v1_state.json"

TICKS = 5000
START_PRICE = 45000.0
SYMBOL = "BTC-USD"

def gen_market():
    price = START_PRICE

    bars_15m = []
    bars_1h = []
    highs = []
    lows = []
    vols = []

    for i in range(TICKS):
        change = random.gauss(0, 0.002)
        price = price * (1 + change)

        high = price * (1 + abs(random.gauss(0, 0.001)))
        low  = price * (1 - abs(random.gauss(0, 0.001)))
        vol = random.uniform(100, 500)

        bars_15m.append(price)
        highs.append(high)
        lows.append(low)
        vols.append(vol)

        if i % 4 == 0:
            bars_1h.append(price)

    return bars_15m, bars_1h, highs, lows, vols

def main():
    print("=== LONG BACKTEST ===")

    subprocess.run(
        "rm -f app/ezcore_v1_state.json logs/ezcore_v1.log logs/ezcore_v1_events.jsonl",
        shell=True
    )

    cfg = CoreConfig()
    bot = CoreV1(cfg)

    bars_15m, bars_1h, highs, lows, vols = gen_market()

    for i in range(len(bars_15m)):
        payload_15m = {SYMBOL: bars_15m[:i+1]}
        payload_1h  = {SYMBOL: bars_1h[:max(1, (i // 4) + 1)]}
        payload_hi  = {SYMBOL: highs[:i+1]}
        payload_lo  = {SYMBOL: lows[:i+1]}
        payload_vol = {SYMBOL: vols[:i+1]}

        bot.tick_paper(
            payload_15m,
            payload_1h,
            payload_hi,
            payload_lo,
            payload_vol
        )

        if i % 500 == 0:
            print("tick", i, "/", TICKS)

    print("backtest complete")

    st = json.load(open(STATE, "r", encoding="utf-8"))
    perf = st.get("perf", {}) or {}

    print("trades:", len(perf.get("trades", []) or []))
    print("open_pos:", perf.get("open_pos"))
    notify_test_complete("EZTRADER test complete")

if __name__ == "__main__":
    main()
