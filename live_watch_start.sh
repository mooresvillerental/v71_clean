#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
cd ~/v71_clean
mkdir -p "$PREFIX/var/run" "$PREFIX/var/log"
PIDF="$PREFIX/var/run/live_watch_btc.pid"
LOG="$PREFIX/var/log/live_watch_btc.log"

# Stop existing
if [ -f "$PIDF" ]; then
  pid="$(cat "$PIDF" 2>/dev/null || true)"
  if [ -n "${pid:-}" ] && kill -0 "$pid" 2>/dev/null; then
    echo "Watcher already running PID=$pid"
    exit 0
  fi
  rm -f "$PIDF"
fi

nohup ./bin/live_watch_btc.sh >>"$LOG" 2>&1 &
echo $! > "$PIDF"
echo "Started watcher PID=$(cat "$PIDF")"
echo "Log: $LOG"
