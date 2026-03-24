#!/data/data/com.termux/files/usr/bin/bash

# ALERT_ON_EXIT_V2: always notify when wrapper exits
trap 'cd "$(dirname "$0")" >/dev/null 2>&1; ./alert_done.sh >/dev/null 2>&1 || true' EXIT


# Run a command, log output, extract final_equity + max_drawdown_usd, then alert.
# Usage:
#   ./bt_run.sh "LABEL" -- python bin/backtest_v2_engine.py ...
set -u

label="${1:-Backtest}"
shift || true

# allow: ./bt_run.sh "Label" -- <cmd...>
if [ "${1:-}" = "--" ]; then shift; fi

ts="$(date +%Y%m%d_%H%M%S)"
log="backtests/run_${ts}.log"

start="$(date +%s)"
# Run and tee log
( "$@" ) 2>&1 | tee "$log"
code="${PIPESTATUS[0]}"
end="$(date +%s)"
secs=$((end-start))

# Extract metrics if present
equity="$(grep -Eo 'final_equity:\s*[0-9]+(\.[0-9]+)?' "$log" | tail -n1 | awk '{print $2}')"
dd="$(grep -Eo 'max_drawdown_usd:\s*[0-9]+(\.[0-9]+)?' "$log" | tail -n1 | awk '{print $2}')"

[ -z "${equity:-}" ] && equity="unknown"
[ -z "${dd:-}" ] && dd="unknown"

./alert_done.sh "$code" "$secs" "$label" "$equity" "$dd"
exit "$code"
