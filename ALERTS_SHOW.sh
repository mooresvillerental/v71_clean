#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/v70_host"
ENV_FILE="${ENV_FILE:-$HOME/v70_host/alerts.env}"
echo "=== EZTrader Alerts State ==="
echo "ENV_FILE: $ENV_FILE"
echo
set +u
# shellcheck disable=SC1090
source "$ENV_FILE" 2>/dev/null || true
set -u

# compute quiet active + effective toggles
quiet_now=0
now_hm="$(date '+%H:%M')"
hhmm_to_min(){ python - "$1" <<'PY'
import sys
h,m=sys.argv[1].strip().split(":")
print(int(h)*60+int(m))
PY
}
in_quiet(){
  local now_min s_min e_min
  now_min="$(hhmm_to_min "$now_hm")"
  s_min="$(hhmm_to_min "${QUIET_START:-22:00}")"
  e_min="$(hhmm_to_min "${QUIET_END:-07:00}")"
  if [ "${s_min}" -le "${e_min}" ]; then
    [ "$now_min" -ge "$s_min" ] && [ "$now_min" -lt "$e_min" ]
  else
    [ "$now_min" -ge "$s_min" ] || [ "$now_min" -lt "$e_min" ]
  fi
}

if [ "${QUIET_ENABLED:-1}" = "1" ] && in_quiet; then quiet_now=1; fi

echo "PRESET_NAME=${PRESET_NAME:-}"
echo "ALERTS_ENABLED=${ALERTS_ENABLED:-1}"
echo "POLL_SEC=${POLL_SEC:-10}"
echo "REPEAT_SEC=${REPEAT_SEC:-0}"
echo "CURL_MAX_TIME=${CURL_MAX_TIME:-3}"
echo "STOP_ON_CONFIRM=${STOP_ON_CONFIRM:-1}"
echo "SPEAK=${SPEAK:-0}"
echo "NOTIFY=${NOTIFY:-1}"
echo "VIBRATE=${VIBRATE:-1}"
echo "QUIET_ENABLED=${QUIET_ENABLED:-1}"
echo "QUIET_START=${QUIET_START:-22:00}"
echo "QUIET_END=${QUIET_END:-07:00}"
echo "QUIET_ALLOW_NOTIFY=${QUIET_ALLOW_NOTIFY:-0}"
echo "QUIET_ALLOW_VIBRATE=${QUIET_ALLOW_VIBRATE:-0}"
echo "QUIET_ALLOW_SPEAK=${QUIET_ALLOW_SPEAK:-0}"
echo "PRICE_MOVE_ENABLED=${PRICE_MOVE_ENABLED:-0}"
echo "PRICE_MOVE_THRESHOLD_PCT=${PRICE_MOVE_THRESHOLD_PCT:-5}"
echo "PRICE_MOVE_WINDOW_MIN=${PRICE_MOVE_WINDOW_MIN:-60}"
echo "PRICE_MOVE_DIRECTION=${PRICE_MOVE_DIRECTION:-both}"
echo "PRICE_MOVE_OVERRIDE_QUIET=${PRICE_MOVE_OVERRIDE_QUIET:-0}"
echo "WAKE_TRADE_ENABLED=${WAKE_TRADE_ENABLED:-0}"
echo "WAKE_TRADE_MIN_USD=${WAKE_TRADE_MIN_USD:-150}"
echo "WAKE_TRADE_OVERRIDE_QUIET=${WAKE_TRADE_OVERRIDE_QUIET:-0}"
echo
echo "QUIET_ACTIVE_NOW=${quiet_now}"
if [ "$quiet_now" = "1" ]; then
  eff_notify="${NOTIFY:-1}"; eff_vib="${VIBRATE:-1}"; eff_speak="${SPEAK:-0}"
  [ "${QUIET_ALLOW_NOTIFY:-0}" = "1" ] || eff_notify="0"
  [ "${QUIET_ALLOW_VIBRATE:-0}" = "1" ] || eff_vib="0"
  [ "${QUIET_ALLOW_SPEAK:-0}" = "1" ] || eff_speak="0"
  echo "EFFECTIVE_NOW: SPEAK=${eff_speak} NOTIFY=${eff_notify} VIBRATE=${eff_vib}"
else
  echo "EFFECTIVE_NOW: SPEAK=${SPEAK:-0} NOTIFY=${NOTIFY:-1} VIBRATE=${VIBRATE:-1}"
fi
echo
echo "Watcher status:"
if [ -f .watch_alerts.pid ]; then
  pid="$(cat .watch_alerts.pid || true)"
  echo "PID file: $pid"
  ps -p "$pid" -o pid,etime,cmd 2>/dev/null || echo "Process: NOT RUNNING"
else
  echo "PID file: (missing)"
  ps aux | grep WATCH_ALERTS | grep -v grep || echo "Process: NOT RUNNING"
fi
echo
echo "Last 8 log lines:"
tail -n 8 logs/watch_alerts.log 2>/dev/null || true
