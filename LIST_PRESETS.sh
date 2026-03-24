#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/v70_host"

mf="presets/manifest.tsv"
echo "=== EZTrader Presets ==="
echo

if [ -f "$mf" ]; then
  # Print from manifest (preferred)
  while IFS=$'\t' read -r name desc; do
    [[ "$name" =~ ^# ]] && continue
    [ -z "${name:-}" ] && continue
    printf "%-12s — %s\n" "$name" "$desc"
  done < "$mf"
else
  echo "manifest missing: $mf"
  echo "Showing preset files:"
  ls -1 presets/*.env 2>/dev/null | sed 's#.*/##; s#\.env$##' || true
fi

echo
echo "Tip: ./APPLY_PRESET.sh notify_only"
echo "Tip: ./RESET_DEFAULTS.sh"
