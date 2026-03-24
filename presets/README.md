# EZTrader Alerts Presets

Presets are *intent-based* switches: “How do I want alerts to behave right now?”

## Included presets

- **balanced** — default, battery-safe, quiet-aware (v1 baseline)
- **notify_only** — notification only (no vibration, no speak)
- **silent** — log only (no notify, no vibrate, no speak)
- **hands_free** — speak only (eyes-off mode)
- **watch_mode** — active trading (repeat reminders on)

## Commands

- List presets:
  - `./LIST_PRESETS.sh`

- Apply preset:
  - `./APPLY_PRESET.sh notify_only`
  - `./APPLY_PRESET.sh balanced`

- Reset to v1 baseline:
  - `./RESET_DEFAULTS.sh`

Notes:
- Applying a preset updates `alerts.env` and sets `PRESET_NAME=<preset>`.
- The watcher reads `alerts.env` each loop, so changes apply live.
