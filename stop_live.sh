#!/data/data/com.termux/files/usr/bin/bash

echo "Stopping EZTRADER live services..."

pkill -f api_server_stdlib.py 2>/dev/null
pkill -f kraken_price_feed.py 2>/dev/null
pkill -f signal_listener.py 2>/dev/null
pkill -f kraken_ohlc_engine.py 2>/dev/null
pkill -f live_candle_engine.py 2>/dev/null

echo "All services stopped."
