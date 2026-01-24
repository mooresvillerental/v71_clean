#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/v70_host"

ENV_FILE="${ENV_FILE:-$HOME/v70_host/alerts.env}"

# minimal safe loader (env must be KEY=VALUE only)
load_env(){
  if [ -f "$ENV_FILE" ]; then
    set +u
    # shellcheck disable=SC1090
    source "$ENV_FILE" || true
    set -u
  fi
}

toggle01(){
  # toggle01 KEY
  local k="$1"
  local cur="${!k:-0}"
  if [ "$cur" = "1" ]; then
    ./ALERTS_SET.sh "$k" 0 >/dev/null
  else
    ./ALERTS_SET.sh "$k" 1 >/dev/null
  fi
}

read_num(){
  local label="$1" def="${2:-}"
  printf "%s [%s]: " "$label" "$def"
  read -r x || true
  x="${x:-}"
  if [ -z "$x" ]; then
    echo ""
    return 0
  fi
  # allow integers or decimals
  python - "$x" <<'PY' >/dev/null 2>&1 || { echo ""; return 0; }
import sys
float(sys.argv[1])
PY
  echo "$x"
}

read_hhmm(){
  local label="$1" def="${2:-22:00}"
  printf "%s [%s]: " "$label" "$def"
  read -r x || true
  x="${x:-}"
  [ -z "$x" ] && { echo ""; return 0; }
  python - "$x" <<'PY' >/dev/null 2>&1 || { echo ""; return 0; }
import sys,re
s=sys.argv[1].strip()
assert re.match(r'^\d\d:\d\d$', s)
h,m=map(int,s.split(':'))
assert 0<=h<=23 and 0<=m<=59
PY
  echo "$x"
}

apply_preset_menu(){
  echo
  echo "Presets:"
  echo " 1) balanced (battery-aware, repeat off)"
  echo " 2) notify_only"
  echo " 3) vibrate_only"
  echo " 4) silent"
  echo " 5) daytime_active"
  echo " 6) night_strict"
  echo " 7) night_wake_big_moves"
  printf "> "
  read -r c || true
  case "${c:-}" in
    1) ./APPLY_PRESET.sh balanced --restart ;;
    2) ./APPLY_PRESET.sh notify_only --restart ;;
    3) ./APPLY_PRESET.sh vibrate_only --restart ;;
    4) ./APPLY_PRESET.sh silent --restart ;;
    5) ./APPLY_PRESET.sh daytime_active --restart ;;
    6) ./APPLY_PRESET.sh night_strict --restart ;;
    7) ./APPLY_PRESET.sh night_wake_big_moves --restart ;;
    *) echo "No change." ;;
  esac
}

show_state(){
  if [ -f ./ALERTS_SHOW.sh ]; then
    ./ALERTS_SHOW.sh
  else
    echo "ALERTS_SHOW.sh not found."
    echo "alerts.env:"
    nl -ba "$ENV_FILE" | sed -n '1,140p'
  fi
}

while true; do
  load_env
  preset="${PRESET_NAME:-custom}"

  echo
  echo "=============================="
  echo " EZTrader Alerts Wizard"
  echo " Preset: $preset"
  echo " ENV: $ENV_FILE"
  echo "=============================="
  echo " 1) Apply preset"
  echo " 2) Reset defaults (balanced)"
  echo " 3) Toggle Alerts Enabled        (ALERTS_ENABLED=${ALERTS_ENABLED:-1})"
  echo " 4) Toggle Notify                (NOTIFY=${NOTIFY:-1})"
  echo " 5) Toggle Vibrate               (VIBRATE=${VIBRATE:-1})"
  echo " 6) Toggle Speak (TTS)           (SPEAK=${SPEAK:-0})"
  echo " 7) Set Poll seconds             (POLL_SEC=${POLL_SEC:-10})"
  echo " 8) Set Repeat seconds (0=off)   (REPEAT_SEC=${REPEAT_SEC:-0})"
  echo " 9) Quiet: toggle enabled        (QUIET_ENABLED=${QUIET_ENABLED:-1})"
  echo "10) Quiet: set start/end         (${QUIET_START:-22:00} -> ${QUIET_END:-07:00})"
  echo "11) Quiet: allow N/V/S           (${QUIET_ALLOW_NOTIFY:-0}/${QUIET_ALLOW_VIBRATE:-0}/${QUIET_ALLOW_SPEAK:-0})"
  echo "---- Advanced (OFF by default) ----"
  echo "12) Wake for big price move      (EN=${PRICE_MOVE_ENABLED:-0} TH=${PRICE_MOVE_THRESHOLD_PCT:-5}% WIN=${PRICE_MOVE_WINDOW_MIN:-60}min DIR=${PRICE_MOVE_DIRECTION:-both} OVR=${PRICE_MOVE_OVERRIDE_QUIET:-0})"
  echo "13) Wake for big trade size      (EN=${WAKE_TRADE_ENABLED:-0} MIN_USD=${WAKE_TRADE_MIN_USD:-150} PCT_CASH=${WAKE_TRADE_PCT_OF_CASH:-0} OVR=${WAKE_TRADE_OVERRIDE_QUIET:-0})"
  echo "----"
  echo "14) Show current state"
  echo "15) Exit"
  printf "> "
  read -r choice || true

  case "${choice:-}" in
    1) apply_preset_menu ;;
    2) ./RESET_DEFAULTS.sh --restart ;;
    3) toggle01 ALERTS_ENABLED ;;
    4) toggle01 NOTIFY ;;
    5) toggle01 VIBRATE ;;
    6) toggle01 SPEAK ;;
    7)
      x="$(read_num "POLL_SEC" "${POLL_SEC:-10}")"
      [ -n "${x:-}" ] && ./ALERTS_SET.sh POLL_SEC "$x" >/dev/null
      ;;
    8)
      x="$(read_num "REPEAT_SEC (0=off)" "${REPEAT_SEC:-0}")"
      [ -n "${x:-}" ] && ./ALERTS_SET.sh REPEAT_SEC "$x" >/dev/null
      ;;
    9) toggle01 QUIET_ENABLED ;;
    10)
      s="$(read_hhmm "QUIET_START" "${QUIET_START:-22:00}")"
      e="$(read_hhmm "QUIET_END" "${QUIET_END:-07:00}")"
      [ -n "${s:-}" ] && ./ALERTS_SET.sh QUIET_START "$s" >/dev/null
      [ -n "${e:-}" ] && ./ALERTS_SET.sh QUIET_END "$e" >/dev/null
      ;;
    11)
      printf "QUIET_ALLOW_NOTIFY (0/1) [%s]: " "${QUIET_ALLOW_NOTIFY:-0}"; read -r a || true
      printf "QUIET_ALLOW_VIBRATE (0/1) [%s]: " "${QUIET_ALLOW_VIBRATE:-0}"; read -r b || true
      printf "QUIET_ALLOW_SPEAK (0/1) [%s]: " "${QUIET_ALLOW_SPEAK:-0}"; read -r c || true
      case "${a:-}" in 0|1) ./ALERTS_SET.sh QUIET_ALLOW_NOTIFY "$a" >/dev/null ;; esac
      case "${b:-}" in 0|1) ./ALERTS_SET.sh QUIET_ALLOW_VIBRATE "$b" >/dev/null ;; esac
      case "${c:-}" in 0|1) ./ALERTS_SET.sh QUIET_ALLOW_SPEAK "$c" >/dev/null ;; esac
      ;;
    12)
      toggle01 PRICE_MOVE_ENABLED
      x="$(read_num "PRICE_MOVE_THRESHOLD_PCT" "${PRICE_MOVE_THRESHOLD_PCT:-5}")"; [ -n "${x:-}" ] && ./ALERTS_SET.sh PRICE_MOVE_THRESHOLD_PCT "$x" >/dev/null
      y="$(read_num "PRICE_MOVE_WINDOW_MIN" "${PRICE_MOVE_WINDOW_MIN:-60}")"; [ -n "${y:-}" ] && ./ALERTS_SET.sh PRICE_MOVE_WINDOW_MIN "$y" >/dev/null
      printf "PRICE_MOVE_DIRECTION (up/down/both) [%s]: " "${PRICE_MOVE_DIRECTION:-both}"; read -r d || true
      d="${d:-}"
      case "$d" in up|down|both) ./ALERTS_SET.sh PRICE_MOVE_DIRECTION "$d" >/dev/null ;; "") : ;; esac
      toggle01 PRICE_MOVE_OVERRIDE_QUIET
      ;;
    13)
      toggle01 WAKE_TRADE_ENABLED
      x="$(read_num "WAKE_TRADE_MIN_USD" "${WAKE_TRADE_MIN_USD:-150}")"; [ -n "${x:-}" ] && ./ALERTS_SET.sh WAKE_TRADE_MIN_USD "$x" >/dev/null
      y="$(read_num "WAKE_TRADE_PCT_OF_CASH (0=off)" "${WAKE_TRADE_PCT_OF_CASH:-0}")"; [ -n "${y:-}" ] && ./ALERTS_SET.sh WAKE_TRADE_PCT_OF_CASH "$y" >/dev/null
      toggle01 WAKE_TRADE_OVERRIDE_QUIET
      ;;
    14) show_state ;;
    15) echo "Bye."; exit 0 ;;
    *) echo "Invalid choice." ;;
  esac

  echo "Saved."
done
