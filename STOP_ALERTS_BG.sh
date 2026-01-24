#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/v70_host"

if [ -f .watch_alerts.pid ]; then
  pid="$(cat .watch_alerts.pid || true)"
  if [ -n "${pid:-}" ]; then
    kill "$pid" >/dev/null 2>&1 || true
  fi
  rm -f .watch_alerts.pid
fi

pkill -f "$HOME/v70_host/WATCH_ALERTS.sh" >/dev/null 2>&1 || true
termux-wake-unlock >/dev/null 2>&1 || true
termux-tts-stop >/dev/null 2>&1 || true
echo "OK: alerts stopped"
