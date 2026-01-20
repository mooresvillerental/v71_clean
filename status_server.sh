#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
cd "$HOME/v70_host"

PIDFILE="run/server.pid"
echo "HEALTH:"
curl -sS "http://127.0.0.1:8080/health" || echo "(health unreachable)"

echo
if [ -f "$PIDFILE" ]; then
  PID="$(cat "$PIDFILE" || true)"
  echo "PIDFILE: $PIDFILE ($PID)"
  ps -o pid,ppid,cmd -p "$PID" 2>/dev/null || echo "(pid not running)"
else
  echo "PIDFILE: (none)"
fi

echo
echo "LAST LOG (tail 40):"
LAST_LOG="$(ls -1t logs/server_*.log 2>/dev/null | head -n 1 || true)"
if [ -n "$LAST_LOG" ]; then
  echo "$LAST_LOG"
  tail -n 40 "$LAST_LOG" || true
else
  echo "(no logs yet)"
fi
