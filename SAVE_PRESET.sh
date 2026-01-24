#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/v70_host"

name="${1:-}"
if [ -z "$name" ]; then
  echo "Usage: ./SAVE_PRESET.sh <new_preset_name>"
  exit 1
fi

if [ ! -f alerts.env ]; then
  echo "ERROR: alerts.env missing"
  exit 1
fi

dst="presets/${name}.env"
if [ -f "$dst" ]; then
  echo "ERROR: preset already exists: $dst"
  exit 1
fi

cp -f alerts.env "$dst"
echo "OK: saved current alerts.env as preset: $dst"
