#!/data/data/com.termux/files/usr/bin/bash

echo "=== RUNNING PROCESSES ==="
ps -ef | grep -E "kraken_ohlc_engine|live_candle_engine|api_server_stdlib" | grep -v grep

echo
echo "=== LATEST SIGNAL ==="
cat signals/latest_signal.json 2>/dev/null

echo
echo "=== LIVE PRICE ==="
cat signals/latest_price.json 2>/dev/null

echo
echo "=== SIGNAL FILE TIMES ==="
python - <<'EOF'
import time
from pathlib import Path

for f in [
    "signals/latest_signal.json",
    "signals/latest_price.json",
    "signals/ohlc_live.json"
]:
    p = Path(f)
    if p.exists():
        print(f, "->", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(p.stat().st_mtime)))
    else:
        print(f, "missing")
EOF

echo
echo "=== LAST 5 ENGINE EVENTS ==="
tail -n 5 live_candle_engine.log 2>/dev/null
