#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/v70_host"

ENVF="${1:-alerts.env}"
[ -f "$ENVF" ] || { echo "ERROR: $ENVF missing"; exit 1; }

tmp="$(mktemp)"

# Default table (every key we care about)
cat > "$tmp" <<'DEF'
ALERTS_ENABLED=1
POLL_SEC=5
REPEAT_SEC=60
CURL_MAX_TIME=3
STOP_ON_CONFIRM=1
SPEAK=0
NOTIFY=1
VIBRATE=1
QUIET_ENABLED=1
QUIET_START=22:00
QUIET_END=07:00
QUIET_ALLOW_NOTIFY=0
QUIET_ALLOW_VIBRATE=0
QUIET_ALLOW_SPEAK=0
PRICE_MOVE_ENABLED=0
PRICE_MOVE_THRESHOLD_PCT=5
PRICE_MOVE_WINDOW_MIN=60
PRICE_MOVE_DIRECTION=both
PRICE_MOVE_OVERRIDE_QUIET=0
WAKE_TRADE_ENABLED=0
WAKE_TRADE_MIN_USD=150
WAKE_TRADE_PCT_OF_CASH=0
WAKE_TRADE_OVERRIDE_QUIET=0
DEF

# Merge: defaults first, then override with existing file values (KEY=VALUE only)
python - <<'PY' "$tmp" "$ENVF" > "$ENVF.normalized"
import sys
from pathlib import Path

defaults = Path(sys.argv[1]).read_text().splitlines()
current  = Path(sys.argv[2]).read_text().splitlines()

def parse(lines):
    out={}
    for ln in lines:
        ln=ln.strip()
        if not ln or ln.startswith("#"): 
            continue
        if "=" not in ln:
            continue
        k,v=ln.split("=",1)
        k=k.strip(); v=v.strip()
        if k:
            out[k]=v
    return out

d=parse(defaults)
c=parse(current)
d.update(c)  # current overrides defaults

# write normalized, stable order using defaults order
order=[ln.split("=",1)[0].strip() for ln in defaults if ln.strip() and not ln.strip().startswith("#") and "=" in ln]
for k in order:
    print(f"{k}={d.get(k,'')}")
PY

bak="${ENVF}.bak_norm_$(date +%Y%m%d_%H%M%S)"
cp -f "$ENVF" "$bak" || true
mv -f "$ENVF.normalized" "$ENVF"

echo "OK: normalized $ENVF"
echo "Backup: $bak"
