#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/v70_host"
echo "=== EZTrader Presets ==="
ls -1 presets/*.env 2>/dev/null | sed 's#.*/##' | sed 's/\.env$//' || echo "(none)"
echo
echo "Usage: ./APPLY_PRESET.sh <name>"
