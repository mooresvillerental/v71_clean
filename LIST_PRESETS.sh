#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/v70_host"
echo "=== Presets ==="
ls -1 presets | sed 's/\.env$//' | sort
