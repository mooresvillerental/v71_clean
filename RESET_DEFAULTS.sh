#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/v70_host"

ts="$(date +%Y%m%d_%H%M%S)"
if [ -f alerts.env ]; then
  cp -f alerts.env "alerts.env.bak_reset_${ts}" 2>/dev/null || true
  echo "Backup: alerts.env.bak_reset_${ts}"
fi

./APPLY_PRESET.sh balanced >/dev/null
echo "OK: defaults restored (balanced)"
