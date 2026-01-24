#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/v70_host"

ENV_FILE="${ENV_FILE:-$HOME/v70_host/alerts.env}"

usage(){
  echo "Usage: ./APPLY_PRESET.sh <preset> [--restart]"
  echo "Presets: balanced notify_only vibrate_only silent daytime_active night_strict night_wake_big_moves"
  exit 2
}

preset="${1:-}"; [ -n "$preset" ] || usage
restart=0
[ "${2:-}" = "--restart" ] && restart=1

ts="$(date '+%Y%m%d_%H%M%S')"
bak="$ENV_FILE.bak_preset_${preset}_${ts}"
[ -f "$ENV_FILE" ] && cp -f "$ENV_FILE" "$bak" 2>/dev/null || true

write_env(){
  cat > "$ENV_FILE" <<ENV
# ===== EZTrader Alerts User Options =====
# Lines must be KEY=VALUE only. Comments must be on their own line.

PRESET_NAME=$preset

ALERTS_ENABLED=1
POLL_SEC=${POLL_SEC}
REPEAT_SEC=${REPEAT_SEC}
CURL_MAX_TIME=${CURL_MAX_TIME}
STOP_ON_CONFIRM=${STOP_ON_CONFIRM}

SPEAK=${SPEAK}
NOTIFY=${NOTIFY}
VIBRATE=${VIBRATE}

QUIET_ENABLED=${QUIET_ENABLED}
QUIET_START=${QUIET_START}
QUIET_END=${QUIET_END}
QUIET_ALLOW_NOTIFY=${QUIET_ALLOW_NOTIFY}
QUIET_ALLOW_VIBRATE=${QUIET_ALLOW_VIBRATE}
QUIET_ALLOW_SPEAK=${QUIET_ALLOW_SPEAK}

# Advanced (OFF by default unless preset enables)
PRICE_MOVE_ENABLED=${PRICE_MOVE_ENABLED}
PRICE_MOVE_THRESHOLD_PCT=${PRICE_MOVE_THRESHOLD_PCT}
PRICE_MOVE_WINDOW_MIN=${PRICE_MOVE_WINDOW_MIN}
PRICE_MOVE_DIRECTION=${PRICE_MOVE_DIRECTION}
PRICE_MOVE_OVERRIDE_QUIET=${PRICE_MOVE_OVERRIDE_QUIET}

WAKE_TRADE_ENABLED=${WAKE_TRADE_ENABLED}
WAKE_TRADE_MIN_USD=${WAKE_TRADE_MIN_USD}
WAKE_TRADE_PCT_OF_CASH=${WAKE_TRADE_PCT_OF_CASH}
WAKE_TRADE_OVERRIDE_QUIET=${WAKE_TRADE_OVERRIDE_QUIET}

# Vibrate behavior
VIBRATE_MS=${VIBRATE_MS}
VIBRATE_BUY=${VIBRATE_BUY}
VIBRATE_SELL=${VIBRATE_SELL}
ENV
  chmod 600 "$ENV_FILE" 2>/dev/null || true
}

# Defaults (battery-aware + sleep-friendly)
POLL_SEC=10
REPEAT_SEC=0
CURL_MAX_TIME=3
STOP_ON_CONFIRM=1

SPEAK=0
NOTIFY=1
VIBRATE=1

QUIET_ENABLED=1
QUIET_START=22:00
QUIET_END=07:00
QUIET_ALLOW_NOTIFY=0
QUIET_ALLOW_VIBRATE=0
QUIET_ALLOW_SPEAK=0

PRICE_MOVE_ENABLED=0
PRICE_MOVE_THRESHOLD_PCT=5
PRICE_MOVE_WINDOW_MIN=60
PRICE_MOVE_DIRECTION=both
PRICE_MOVE_OVERRIDE_QUIET=0

WAKE_TRADE_ENABLED=0
WAKE_TRADE_MIN_USD=150
WAKE_TRADE_PCT_OF_CASH=0
WAKE_TRADE_OVERRIDE_QUIET=0

VIBRATE_MS=800
VIBRATE_BUY=120,120,120
VIBRATE_SELL=500,180,500

case "$preset" in
  balanced)
    # already set
    ;;
  notify_only)
    VIBRATE=0
    SPEAK=0
    NOTIFY=1
    ;;
  vibrate_only)
    NOTIFY=0
    SPEAK=0
    VIBRATE=1
    ;;
  silent)
    NOTIFY=0
    SPEAK=0
    VIBRATE=0
    ;;
  daytime_active)
    # No quiet enforcement, no repeats, notify+vibrate
    QUIET_ENABLED=0
    REPEAT_SEC=0
    NOTIFY=1
    VIBRATE=1
    SPEAK=0
    ;;
  night_strict)
    # Quiet enforced; no overrides; no repeats
    QUIET_ENABLED=1
    QUIET_ALLOW_NOTIFY=0
    QUIET_ALLOW_VIBRATE=0
    QUIET_ALLOW_SPEAK=0
    REPEAT_SEC=0
    ;;
  night_wake_big_moves)
    # Quiet enforced, BUT allow wake on big moves / big trades (advanced toggles ON, overrides ON)
    QUIET_ENABLED=1
    QUIET_ALLOW_NOTIFY=0
    QUIET_ALLOW_VIBRATE=0
    QUIET_ALLOW_SPEAK=0

    PRICE_MOVE_ENABLED=1
    PRICE_MOVE_THRESHOLD_PCT=5
    PRICE_MOVE_WINDOW_MIN=60
    PRICE_MOVE_DIRECTION=both
    PRICE_MOVE_OVERRIDE_QUIET=1

    WAKE_TRADE_ENABLED=1
    WAKE_TRADE_MIN_USD=150
    WAKE_TRADE_PCT_OF_CASH=0
    WAKE_TRADE_OVERRIDE_QUIET=1

    REPEAT_SEC=0
    ;;
  *)
    usage
    ;;
esac

write_env

echo "OK: applied preset '$preset' -> $ENV_FILE"
[ -f "$bak" ] && echo "Backup: $bak"

if [ "$restart" = "1" ]; then
  if [ -f ./START_ALERTS_BG.sh ]; then
    ./START_ALERTS_BG.sh
  else
    echo "NOTE: START_ALERTS_BG.sh not found; restart skipped."
  fi
fi
