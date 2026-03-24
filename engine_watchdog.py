import os
import time
import subprocess
from pathlib import Path

CHECK_INTERVAL = 60

PROCESSES = {
    "kraken_ohlc_engine.py": "nohup python -u kraken_ohlc_engine.py > kraken_ohlc_engine.log 2>&1 &",
    "live_candle_engine.py": "nohup python -u live_candle_engine.py > live_candle_engine.log 2>&1 &",
    "api_server_stdlib.py": "nohup python -u api_server_stdlib.py > api_server_stdlib.log 2>&1 &"
}

SIGNAL_FILE = Path("signals/latest_signal.json")

def process_running(name):
    result = subprocess.run(
        f"ps -ef | grep {name} | grep -v grep",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    return bool(result.stdout)

def restart_process(name):
    print(f"Restarting {name}")
    subprocess.run(PROCESSES[name], shell=True)

def signal_stale():
    if not SIGNAL_FILE.exists():
        return True
    age = time.time() - SIGNAL_FILE.stat().st_mtime
    return age > 180

print("EZTrader Watchdog running...")

while True:

    for name in PROCESSES:

        if not process_running(name):
            restart_process(name)

    if signal_stale():
        print("Signal file stale — restarting signal engine")
        subprocess.run("pkill -f live_candle_engine.py", shell=True)
        restart_process("live_candle_engine.py")

    time.sleep(CHECK_INTERVAL)
