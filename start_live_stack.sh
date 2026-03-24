#!/data/data/com.termux/files/usr/bin/bash

echo "Stopping old EZTRADER processes..."

pkill -f api_server_stdlib.py 2>/dev/null
pkill -f kraken_ohlc_engine.py 2>/dev/null
pkill -f live_candle_engine.py 2>/dev/null

sleep 1

echo "Starting EZTRADER live stack..."

nohup python -u api_server_stdlib.py > ez_api.log 2>&1 &
nohup python -u kraken_ohlc_engine.py > ohlc_engine.log 2>&1 &
nohup python -u live_candle_engine.py > candle_engine.log 2>&1 &
nohup python -u ez_autopost.py > ez_autopost.log 2>&1 &

sleep 2

echo ""
echo "EZTRADER LIVE STACK STARTED"
echo ""

ps -ef | grep python | grep -E "api_server|ohlc|candle" | grep -v grep

echo ""
echo "Latest Signal:"
cat signals/latest_signal.json
echo ""
