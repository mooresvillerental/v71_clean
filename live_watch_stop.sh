#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
PIDF="$PREFIX/var/run/live_watch_btc.pid"
if [ ! -f "$PIDF" ]; then
  echo "No PID file."
  exit 0
fi
pid="$(cat "$PIDF" 2>/dev/null || true)"
if [ -n "${pid:-}" ] && kill -0 "$pid" 2>/dev/null; then
  kill "$pid" 2>/dev/null || true
  sleep 1
fi
rm -f "$PIDF"
echo "Stopped watcher."
