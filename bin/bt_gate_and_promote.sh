#!/usr/bin/env bash
set -euo pipefail

# =========================================================
# FORGE_NOTIFY_V3
# - No preset volume (side buttons control media volume)
# - Never exits early on per-slice FAIL
# - Always notifies/speaks on exit via trap
# =========================================================

STATUS="FAIL"   # will flip to PASS only if robust gate passes

notify_done() {
  local status="${1:-$STATUS}"
  local msg="Gate ${status}: ${LABEL:-?} ${DAYS:-?}d | pass ${pass_count:-0}/${offset_count:-0} | avg ${avg_final:-0} | worstDD ${worst_dd:-0}"

  echo ""
  echo "=== ${msg} ==="

  if command -v termux-notification >/dev/null 2>&1; then
    termux-notification --title "EZTrader Gate ${status}" --content "${msg}" --priority high >/dev/null 2>&1 || true
  fi

  if command -v termux-tts-speak >/dev/null 2>&1; then
    # No --volume flag => your side buttons control it
    termux-tts-speak "${msg}" >/dev/null 2>&1 || true
  fi

  for _ in 1 2 3; do printf "\a"; sleep 1; done
}

# Always notify on exit (even if set -e kills us)
on_exit() {
  local rc=$?
  # If we died unexpectedly and never computed avg_final, etc., still speak something useful
  if [ "${rc}" -ne 0 ] && [ "${STATUS}" != "PASS" ]; then
    STATUS="FAIL"
  fi
  notify_done "$STATUS"
}
trap on_exit EXIT

LABEL="${1:-}"
OFFSETS="${2:-}"
shift 2 || true

if [ -z "${LABEL}" ] || [ -z "${OFFSETS}" ]; then
  echo "Usage: ./bin/bt_gate_and_promote.sh \"LABEL\" \"OFFSETS\" -- <backtest args...>"
  exit 2
fi

if [ "${1:-}" != "--" ]; then
  echo "ERROR: missing -- separator before backtest args"
  exit 2
fi
shift

# ---- PASS RULES (per-slice) ----
MIN_FINAL_EQUITY="${MIN_FINAL_EQUITY:-5000.0}"
MAX_DD_USD="${MAX_DD_USD:-500.0}"
MIN_TRADES="${MIN_TRADES:-30}"

# ---- ROBUST RULES (across offsets) ----
MIN_PASS_COUNT="${MIN_PASS_COUNT:-0}"   # 0 disables
WORST_DD_USD="${WORST_DD_USD:-0}"       # 0 disables
AVG_MIN_FINAL="${AVG_MIN_FINAL:-0}"     # 0 disables

# ---- Backtest window ----
DAYS="${DAYS:-90}"

echo "Running gated backtests:"
echo "  LABEL          : $LABEL"
echo "  OFFSETS        : $OFFSETS"
echo "  PASS RULE      : final>=${MIN_FINAL_EQUITY} dd<=${MAX_DD_USD} trades>=${MIN_TRADES}"
echo "  ROBUST RULES   : pass_count>=${MIN_PASS_COUNT} worst_dd<=${WORST_DD_USD} avg_final>=${AVG_MIN_FINAL}"
echo ""

pass_count=0
total_final=0
worst_dd=0
offset_count=$(echo "$OFFSETS" | wc -w | tr -d " ")
avg_final=0

for OFF in $OFFSETS; do
  echo "=================================================="
  echo "$LABEL | ${DAYS}d off${OFF}"
  echo "=================================================="

  OUT="$(python bin/backtest_v2_engine.py --days "$DAYS" --offset-days "$OFF" "$@" 2>&1 | tee /dev/stderr)"

  FE="$(printf "%s\n" "$OUT" | awk -F": " "/^final_equity:/ {print \$2; exit}")"
  DD="$(printf "%s\n" "$OUT" | awk -F": " "/^max_drawdown_usd:/ {print \$2; exit}")"
  TR="$(printf "%s\n" "$OUT" | awk -F": " "/^trades_total:/ {print \$2; exit}" | awk "{print \$1}")"

  if [ -z "${FE:-}" ] || [ -z "${DD:-}" ] || [ -z "${TR:-}" ]; then
    echo "FAIL(off${OFF}): could not parse metrics."
    continue
  fi

  total_final="$(python -c "print(float(\"$total_final\") + float(\"$FE\"))")"
  worst_dd="$(python -c "print(max(float(\"$worst_dd\"), float(\"$DD\")))")"

  # IMPORTANT: don’t let this FAIL exit the script under set -e
  set +e
  python - <<PY
fe=float("$FE"); dd=float("$DD"); tr=int("$TR")
min_fe=float("$MIN_FINAL_EQUITY"); max_dd=float("$MAX_DD_USD"); min_tr=int("$MIN_TRADES")
ok = (fe>=min_fe) and (dd<=max_dd) and (tr>=min_tr)
print("METRICS(off${OFF}): final=%.2f dd=%.2f trades=%d -> %s" % (fe, dd, tr, "PASS" if ok else "FAIL"))
raise SystemExit(0 if ok else 1)
PY
  rc=$?
  set -e

  if [ $rc -eq 0 ]; then
    pass_count=$((pass_count+1))
  fi
done

avg_final="$(python -c "print(float(\"$total_final\")/int(\"$offset_count\") if int(\"$offset_count\") else 0.0)")"

echo ""
echo "==================== SUMMARY ===================="
echo "pass_count=$pass_count/$offset_count"
echo "avg_final=$avg_final"
echo "worst_dd=$worst_dd"
echo "================================================="

robust_ok=1

if [ "$MIN_PASS_COUNT" -gt 0 ] && [ "$pass_count" -lt "$MIN_PASS_COUNT" ]; then
  robust_ok=0
fi

if [ "$WORST_DD_USD" != "0" ]; then
  python -c "import sys; sys.exit(0 if float(\"$worst_dd\") <= float(\"$WORST_DD_USD\") else 1)" || robust_ok=0
fi

if [ "$AVG_MIN_FINAL" != "0" ]; then
  python -c "import sys; sys.exit(0 if float(\"$avg_final\") >= float(\"$AVG_MIN_FINAL\") else 1)" || robust_ok=0
fi

if [ "$robust_ok" -ne 1 ]; then
  echo "ROBUST_GATE: FAIL"
  STATUS="FAIL"
  exit 1
fi

echo "ROBUST_GATE: PASS"
STATUS="PASS"

if [ -x ./bin/promote_to_app.sh ]; then
  ./bin/promote_to_app.sh "$LABEL"
else
  echo "NOTE: promote_to_app.sh not found/executable. Promotion skipped."
fi
