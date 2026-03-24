#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

# forge_notify.sh
# Usage:
#   ./bin/forge_notify.sh "LABEL" -- bash -lc 'set -o pipefail; python ... | tail -n 20'
#
# PASS/FAIL logic:
#   - Default PASS if final_equity >= start_cash AND rc==0
#   - Can override with env:
#       PASS_IF_PROFIT=0  (then PASS if rc==0 only)
#   No preset volume: side buttons control media volume.

LABEL="${1:-TEST}"
shift || true

if [ "${1:-}" != "--" ]; then
  echo "ERROR: missing -- separator."
  echo "Usage: ./bin/forge_notify.sh \"LABEL\" -- <command...>"
  exit 2
fi
shift

PASS_IF_PROFIT="${PASS_IF_PROFIT:-1}"

start_ts="$(date +%s)"
tmp="$(mktemp)"
rc=0

# run command, capture all output, preserve return code
set +e
("$@") 2>&1 | tee "$tmp"
rc="${PIPESTATUS[0]}"
set -e

end_ts="$(date +%s)"
dur="$((end_ts - start_ts))"

# parse metrics if present
start_cash="$(awk -F': ' '/^start_cash:/ {print $2; exit}' "$tmp" | tr -d '\r')"
final_equity="$(awk -F': ' '/^final_equity:/ {print $2; exit}' "$tmp" | tr -d '\r')"
max_dd="$(awk -F': ' '/^max_drawdown_usd:/ {print $2; exit}' "$tmp" | tr -d '\r')"
trades="$(awk -F': ' '/^trades_total:/ {print $2; exit}' "$tmp" | awk '{print $1}' | tr -d '\r')"

status="FAIL"
reason="rc=$rc"

if [ "$rc" -eq 0 ]; then
  if [ "$PASS_IF_PROFIT" = "0" ]; then
    status="PASS"
    reason="rc=0"
  else
    if [ -n "${start_cash:-}" ] && [ -n "${final_equity:-}" ]; then
      # numeric compare via python to avoid bc dependency
      py_ok="$(python - <<PY 2>/dev/null
sc=float("${start_cash}")
fe=float("${final_equity}")
print("1" if fe>=sc else "0")
PY
)"
      if [ "${py_ok:-0}" = "1" ]; then
        status="PASS"
        reason="profit"
      else
        status="FAIL"
        reason="lost_money"
      fi
    else
      # if we can't parse metrics, fall back to rc
      status="PASS"
      reason="rc=0_no_metrics"
    fi
  fi
fi

msg="Test ${status}: ${LABEL} (${dur}s) | ${reason}"
if [ -n "${start_cash:-}" ] && [ -n "${final_equity:-}" ]; then
  msg="${msg} | start ${start_cash} -> final ${final_equity}"
fi
if [ -n "${max_dd:-}" ]; then
  msg="${msg} | dd ${max_dd}"
fi
if [ -n "${trades:-}" ]; then
  msg="${msg} | trades ${trades}"
fi

echo ""
echo "=== ${msg} ==="

# Android notification
if command -v termux-notification >/dev/null 2>&1; then
  termux-notification --title "EZTrader ${status}" --content "${msg}" --priority high >/dev/null 2>&1 || true
fi

# Speak (NO preset volume)
if command -v termux-tts-speak >/dev/null 2>&1; then
  termux-tts-speak "${msg}" >/dev/null 2>&1 || true
fi

# Beep x3
for _ in 1 2 3; do printf "\a"; sleep 1; done

# clean
rm -f "$tmp" >/dev/null 2>&1 || true

exit "$rc"
