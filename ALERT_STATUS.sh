#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/v70_host"
echo "=== EZTrader Alerts Status ==="
if [ -f .watch_alerts.pid ]; then
  pid="$(cat .watch_alerts.pid || true)"
  echo "PID file: $pid"
else
  echo "PID file: (missing)"
fi
echo
ps aux | grep WATCH_ALERTS | grep -v grep || echo "Process: NOT RUNNING"
echo
echo "Last 10 log lines:"
tail -n 10 logs/watch_alerts.log 2>/dev/null || echo "(no log yet)"
