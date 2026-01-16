#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
cd ~/v70_host || exit 1

if [ -f server.pid ]; then
  PID="$(cat server.pid || true)"
  if [ -n "${PID}" ] && kill -0 "${PID}" 2>/dev/null; then
    kill "${PID}" 2>/dev/null || true
    sleep 1
  fi
  rm -f server.pid
fi
