#!/data/data/com.termux/files/usr/bin/bash
export PRICE_MODE=live
set -euo pipefail

cd "$HOME/v70_host"

termux-wake-lock >/dev/null 2>&1 || true

mkdir -p logs run

LOG="logs/server_$(date +%Y%m%d_%H%M%S).log"
PIDFILE="run/server.pid"

# Stop anything already listening on 8080 (best effort)
if command -v lsof >/dev/null 2>&1; then
  OLD_PID="$(lsof -ti tcp:8080 2>/dev/null || true)"
  if [ -n "${OLD_PID}" ]; then
    kill "${OLD_PID}" 2>/dev/null || true
    sleep 0.3
  fi
fi

# Also stop via your script (best effort)
./stop_server.sh >/dev/null 2>&1 || true

# Start
nohup ./start_server.sh >"$LOG" 2>&1 & echo $! > "$PIDFILE"

# Wait briefly and verify health
sleep 0.7
if curl -fsS "http://127.0.0.1:8080/health" >/dev/null; then
  echo "OK: server up"
  echo "PID: $(cat "$PIDFILE")"
  echo "LOG: $LOG"
  echo "OPEN: http://127.0.0.1:8080/trade?ts=$(date +%s)"
else
  echo "FAIL: server did not come up. Last 80 log lines:"
  tail -n 80 "$LOG" || true
  exit 1
fi