#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/v70_host"

# Prevent duplicates
./STOP_ALERTS_BG.sh >/dev/null 2>&1 || true
pkill -f "$HOME/v70_host/WATCH_ALERTS.sh" >/dev/null 2>&1 || true

termux-wake-lock >/dev/null 2>&1 || true

# Run in background; config is read from alerts.env each loop
nohup env ENV_FILE="$HOME/v70_host/alerts.env" LOG="$HOME/v70_host/logs/watch_alerts.log" ./WATCH_ALERTS.sh >/dev/null 2>&1 &
echo $! > .watch_alerts.pid

echo "OK: alerts running in background. PID=$(cat .watch_alerts.pid)"
echo "Main log: $HOME/v70_host/logs/watch_alerts.log"
