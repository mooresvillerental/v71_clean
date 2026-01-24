#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/v70_host"
k="${1:-}"; v="${2:-}"
[ -n "$k" ] || { echo "Usage: ./ALERTS_SET.sh KEY VALUE"; exit 1; }

# sanitize KEY
echo "$k" | grep -Eq '^[A-Z0-9_]+$' || { echo "Bad KEY"; exit 1; }

# rewrite env safely
tmp="$(mktemp)"
touch alerts.env
awk -v K="$k" -v V="$v" '
  BEGIN{found=0}
  /^[[:space:]]*#/ {print; next}
  /^[[:space:]]*$/ {print; next}
  {
    split($0,a,"="); key=a[1]
    if(key==K){ print K"="V; found=1; next }
    print
  }
  END{ if(!found){ print K"="V } }
' alerts.env > "$tmp"
mv "$tmp" alerts.env
chmod 600 alerts.env || true
echo "OK: set $k=$v in $HOME/v70_host/alerts.env"
