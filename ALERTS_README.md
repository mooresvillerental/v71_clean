# EZTrader Alerts (Termux) — v1

This alerts framework runs alongside the EZTrader server and watches `/reco` to notify you when a BUY/SELL is active.

## Quick start
- Start (background):
  ./START_ALERTS_BG.sh
- Stop:
  ./STOP_ALERTS_BG.sh
- Show current state:
  ./ALERTS_SHOW.sh
- Wizard:
  ./ALERTS_WIZARD.sh
- Apply a preset:
  ./APPLY_PRESET.sh balanced
  ./APPLY_PRESET.sh notify_only
  ./APPLY_PRESET.sh silent

## Core concepts
- **alerts.env** is the source of truth.
- The watcher reloads alerts.env each loop, so changes apply quickly.
- Quiet hours are supported; advanced “wake” overrides exist but default OFF.

## Common settings (alerts.env)
- ALERTS_ENABLED=1            # master on/off
- POLL_SEC=5                  # how often to poll /reco
- REPEAT_SEC=60               # repeat reminder interval (0 disables repeats)
- NOTIFY=1                    # Android notifications
- VIBRATE=1                   # vibration
- SPEAK=0                     # Termux TTS voice
- STOP_ON_CONFIRM=1           # stop alerts after a new confirm (optional)

## Quiet hours
- QUIET_ENABLED=1
- QUIET_START=22:00
- QUIET_END=07:00
- QUIET_ALLOW_NOTIFY=0
- QUIET_ALLOW_VIBRATE=0
- QUIET_ALLOW_SPEAK=0

Quiet hours default to **fully silent**. You can allow notify/vibrate/speak selectively.

## Advanced (OFF by default)
- PRICE_MOVE_ENABLED=0
  - PRICE_MOVE_THRESHOLD_PCT=5
  - PRICE_MOVE_WINDOW_MIN=60
  - PRICE_MOVE_DIRECTION=both
  - PRICE_MOVE_OVERRIDE_QUIET=0

- WAKE_TRADE_ENABLED=0
  - WAKE_TRADE_MIN_USD=150
  - WAKE_TRADE_OVERRIDE_QUIET=0

## Battery notes
- POLL_SEC is the main cost driver.
  - 5s = very responsive, higher battery
  - 10–20s = good balance
  - 30–60s = low battery usage
- Use REPEAT_SEC=0 unless you really need reminders.
