#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/v70_host"

name="${1:-}"
if [ -z "$name" ]; then
  echo "Usage: ./APPLY_PRESET.sh <preset_name>"
  echo "Try:  ./LIST_PRESETS.sh"
  exit 2
fi

preset_file="$HOME/v70_host/presets/${name}.env"
if [ ! -f "$preset_file" ]; then
  echo "ERROR: preset not found: $name"
  echo "Try:  ./LIST_PRESETS.sh"
  exit 2
fi

envfile="$HOME/v70_host/alerts.env"
ts="$(date +%Y%m%d_%H%M%S)"
if [ -f "$envfile" ]; then
  cp -f "$envfile" "$envfile.bak_preset_${name}_${ts}" 2>/dev/null || true
  echo "Backup: $(basename "$envfile").bak_preset_${name}_${ts}"
fi

# Write preset as alerts.env
cp -f "$preset_file" "$envfile"

# Ensure PRESET_NAME exists and matches
if grep -q '^PRESET_NAME=' "$envfile"; then
  sed -i "s/^PRESET_NAME=.*/PRESET_NAME=${name}/" "$envfile"
else
  printf "\nPRESET_NAME=%s\n" "$name" >> "$envfile"
fi

echo "OK: applied preset '$name' -> $envfile"
