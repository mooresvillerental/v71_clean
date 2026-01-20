#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

cd "$HOME/v70_host"

INTERVAL=20   # seconds between checks
FAILS=0
MAX_FAILS=2  # restart after N failed health checks

echo "watchdog started at $(date)"

while true; do
  if curl -fsS http://127.0.0.1:8080/health >/dev/null; then
    FAILS=0
  else
    FAILS=$((FAILS+1))
    echo "$(date) health fail ($FAILS/$MAX_FAILS)"
  fi

  if [ "$FAILS" -ge "$MAX_FAILS" ]; then
    echo "$(date) restarting server"
    ./run_boring.sh || true
    FAILS=0
  fi

  sleep "$INTERVAL"
done
