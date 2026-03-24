#!/data/data/com.termux/files/usr/bin/bash

echo "Stopping old live processes..."
pkill -f api_server_stdlib.py 2>/dev/null
pkill -f kraken_price_feed.py 2>/dev/null
pkill -f signal_listener.py 2>/dev/null
pkill -f kraken_ohlc_engine.py 2>/dev/null
pkill -f live_candle_engine.py 2>/dev/null

sleep 1

echo "Starting API..."
nohup python -u api_server_stdlib.py > ez_api.log 2>&1 &

echo "Starting Kraken OHLC engine..."
nohup python -u kraken_ohlc_engine.py > kraken_ohlc.log 2>&1 &

echo "Starting live candle engine..."
nohup python -u live_candle_engine.py > live_candle_engine.log 2>&1 &

sleep 3

echo ""
echo "=== LIVE SYSTEM STARTED ==="
curl http://127.0.0.1:8000/latest-signal
echo ""
