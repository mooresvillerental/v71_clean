#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/v70_host"

LOG="${LOG:-$HOME/v70_host/logs/watch_alerts.log}"
MAX_KB="${MAX_KB:-256}"   # keep at most ~256KB by default
KEEP_LINES="${KEEP_LINES:-400}"

mkdir -p "$(dirname "$LOG")" >/dev/null 2>&1 || true
[ -f "$LOG" ] || exit 0

kb=$(du -k "$LOG" | awk '{print $1}' || echo 0)
if [ "${kb:-0}" -gt "$MAX_KB" ]; then
  ts="$(date +%Y%m%d_%H%M%S)"
  cp "$LOG" "${LOG}.bak_${ts}" >/dev/null 2>&1 || true
  tail -n "$KEEP_LINES" "$LOG" > "${LOG}.tmp" && mv "${LOG}.tmp" "$LOG"
  echo "$(date '+%Y-%m-%d %H:%M:%S') | LOG ROTATED (kept last ${KEEP_LINES} lines)" >> "$LOG" || true
  echo "OK: rotated $LOG (was ${kb}KB)"
else
  echo "OK: log size ${kb}KB <= ${MAX_KB}KB (no rotate)"
fi
