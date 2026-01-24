#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/v70_host"

ENV_FILE="${ENV_FILE:-$HOME/v70_host/alerts.env}"

setv(){
  local k="$1" v="$2"
  if grep -qE "^${k}=" "$ENV_FILE"; then
    # replace
    sed -i "s|^${k}=.*|${k}=${v}|" "$ENV_FILE"
  else
    # append
    printf "%s=%s\n" "$k" "$v" >> "$ENV_FILE"
  fi
}

apply_preset(){
  local p="${1:-}"
  case "$p" in
    silent-night)
      # No interruptions during quiet hours. Outside quiet, still allow notify/vibrate (user can toggle).
      setv ALERTS_ENABLED 1
      setv POLL_SEC 5
      setv REPEAT_SEC 60
      setv STOP_ON_CONFIRM 1

      setv NOTIFY 1
      setv VIBRATE 1
      setv SPEAK 0

      setv QUIET_ENABLED 1
      setv QUIET_START 22:00
      setv QUIET_END 07:00
      setv QUIET_ALLOW_NOTIFY 0
      setv QUIET_ALLOW_VIBRATE 0
      setv QUIET_ALLOW_SPEAK 0

      # Future wake features OFF by default
      setv PRICE_MOVE_ENABLED 0
      setv PRICE_MOVE_OVERRIDE_QUIET 0
      setv WAKE_TRADE_ENABLED 0
      setv WAKE_TRADE_OVERRIDE_QUIET 0
      ;;

    balanced)
      # Normal operations; gentle reminders; no TTS by default.
      setv ALERTS_ENABLED 1
      setv POLL_SEC 5
      setv REPEAT_SEC 60
      setv STOP_ON_CONFIRM 1

      setv NOTIFY 1
      setv VIBRATE 1
      setv SPEAK 0

      setv QUIET_ENABLED 1
      setv QUIET_START 22:00
      setv QUIET_END 07:00
      setv QUIET_ALLOW_NOTIFY 0
      setv QUIET_ALLOW_VIBRATE 0
      setv QUIET_ALLOW_SPEAK 0

      setv PRICE_MOVE_ENABLED 0
      setv PRICE_MOVE_OVERRIDE_QUIET 0
      setv WAKE_TRADE_ENABLED 0
      setv WAKE_TRADE_OVERRIDE_QUIET 0
      ;;

    aggressive)
      # More frequent reminders, still respects quiet hours (no wake).
      setv ALERTS_ENABLED 1
      setv POLL_SEC 5
      setv REPEAT_SEC 15
      setv STOP_ON_CONFIRM 1

      setv NOTIFY 1
      setv VIBRATE 1
      setv SPEAK 0

      setv QUIET_ENABLED 1
      setv QUIET_START 22:00
      setv QUIET_END 07:00
      setv QUIET_ALLOW_NOTIFY 0
      setv QUIET_ALLOW_VIBRATE 0
      setv QUIET_ALLOW_SPEAK 0

      setv PRICE_MOVE_ENABLED 0
      setv PRICE_MOVE_OVERRIDE_QUIET 0
      setv WAKE_TRADE_ENABLED 0
      setv WAKE_TRADE_OVERRIDE_QUIET 0
      ;;

    wake-big-moves)
      # Still quiet by default, but allows OVERRIDE options for future “wake me” triggers.
      # NOTE: watcher may not act on these keys until we implement the trigger logic.
      setv ALERTS_ENABLED 1
      setv POLL_SEC 5
      setv REPEAT_SEC 60
      setv STOP_ON_CONFIRM 1

      setv NOTIFY 1
      setv VIBRATE 1
      setv SPEAK 0

      setv QUIET_ENABLED 1
      setv QUIET_START 22:00
      setv QUIET_END 07:00
      setv QUIET_ALLOW_NOTIFY 0
      setv QUIET_ALLOW_VIBRATE 0
      setv QUIET_ALLOW_SPEAK 0

      # Future wake triggers ON (but override quiet only if user wants)
      setv PRICE_MOVE_ENABLED 1
      setv PRICE_MOVE_THRESHOLD_PCT 5
      setv PRICE_MOVE_WINDOW_MIN 60
      setv PRICE_MOVE_DIRECTION BOTH
      setv PRICE_MOVE_OVERRIDE_QUIET 1

      setv WAKE_TRADE_ENABLED 1
      setv WAKE_TRADE_MIN_USD 250
      setv WAKE_TRADE_PCT_OF_CASH 2.5
      setv WAKE_TRADE_OVERRIDE_QUIET 1
      ;;

    *)
      echo "Usage: $0 {silent-night|balanced|aggressive|wake-big-moves}"
      exit 1
      ;;
  esac

  echo "OK: applied preset: $p"
  echo "File: $ENV_FILE"
}

apply_preset "$@"
