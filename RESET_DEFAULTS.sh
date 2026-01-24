#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/v70_host"
./APPLY_PRESET.sh balanced "${1:-}"
echo "OK: defaults restored (balanced)"
