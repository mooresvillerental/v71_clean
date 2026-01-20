#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

echo "🛑 Stopping old server (if any)..."
./stop_server.sh >/dev/null 2>&1 || true

echo "🚀 Starting EZTrader..."
./start_server.sh

sleep 1

URL="http://127.0.0.1:8080/trade?ts=$(date +%s)"
echo
echo "✅ EZTrader is LIVE"
echo "👉 OPEN THIS: $URL"
echo
