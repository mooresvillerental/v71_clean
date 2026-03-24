#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   DAYS=365 OFFSETS="0 270 540 810" ./bin/bt_matrix_score.sh configs.txt -- <common backtest args>
#
# configs.txt = one label per line, like:
#   CFG1|--rsi-buy 38 --rsi-sell 60 --trade-pct 0.50 --macro-mode --macro-ema-len 200 --macro-symbol BTC-USD
#   CFG2|--rsi-buy 42 --rsi-sell 62 --trade-pct 0.35 --regime-mode --regime-symbol BTC-USD --regime-ema-len 200

CONFIG_FILE="${1:-}"
shift || true

if [ -z "$CONFIG_FILE" ] || [ ! -f "$CONFIG_FILE" ]; then
  echo "ERROR: config file missing. Provide a configs.txt file."
  exit 2
fi

if [ "${1:-}" != "--" ]; then
  echo "ERROR: missing -- separator before common args"
  exit 2
fi
shift

DAYS="${DAYS:-365}"
OFFSETS="${OFFSETS:-0 270 540 810}"
OUTCSV="backtests/MATRIX_SCORE.csv"
RUNTS="$(date +%Y%m%d_%H%M%S)"
OUTLOG="backtests/matrix_${RUNTS}.log"

# Scoring weights (consistency-first)
# score = min_final + 0.25*avg_final - 0.75*worst_dd
# (simple, stable, and hard to game)
echo "run_ts,label,days,offsets,pass_count,offset_count,avg_final,worst_dd,min_final,score" > "$OUTCSV"

notify_all_done() {
  local msg="MATRIX DONE ${DAYS}d | results: $(wc -l < "$OUTCSV") rows | $(basename "$OUTCSV")"
  echo "=== $msg ==="
  if command -v termux-notification >/dev/null 2>&1; then
    termux-notification --title "EZTrader Matrix Done" --content "$msg" --priority high >/dev/null 2>&1 || true
  fi
  if command -v termux-tts-speak >/dev/null 2>&1; then
    termux-tts-speak "$msg" >/dev/null 2>&1 || true
  fi
}

echo "Writing log: $OUTLOG"
{
  echo "MATRIX START $RUNTS"
  echo "DAYS=$DAYS"
  echo "OFFSETS=$OFFSETS"
  echo "CONFIG_FILE=$CONFIG_FILE"
  echo
} | tee "$OUTLOG" >/dev/null

while IFS= read -r line; do
  [ -z "${line// /}" ] && continue
  [[ "$line" =~ ^# ]] && continue

  label="${line%%|*}"
  args="${line#*|}"

  echo "=== RUN: $label ===" | tee -a "$OUTLOG"

  # Run gate script, but override the gate thresholds to be more “consistency-first”
  # You can change these anytime.
  DAYS="$DAYS" MIN_FINAL_EQUITY="${MIN_FINAL_EQUITY:-5000}" MAX_DD_USD="${MAX_DD_USD:-1800}" MIN_TRADES="${MIN_TRADES:-200}" \
  MIN_PASS_COUNT="${MIN_PASS_COUNT:-3}" WORST_DD_USD="${WORST_DD_USD:-2200}" AVG_MIN_FINAL="${AVG_MIN_FINAL:-5200}" \
  ./bin/bt_gate_and_promote.sh "$label" "$OFFSETS" -- $args "$@" 2>&1 | tee -a "$OUTLOG" || true

  # Parse summary metrics from the log tail for this run
  # We rely on your gate script’s SUMMARY lines.
  pass_count="$(tac "$OUTLOG" | awk -F= "/^pass_count=/{print \$2; exit}" | tr -d " " | awk -F/ "{print \$1}")"
  offset_count="$(tac "$OUTLOG" | awk -F= "/^pass_count=/{print \$2; exit}" | tr -d " " | awk -F/ "{print \$2}")"
  avg_final="$(tac "$OUTLOG" | awk -F= "/^avg_final=/{print \$2; exit}" | tr -d " ")"
  worst_dd="$(tac "$OUTLOG" | awk -F= "/^worst_dd=/{print \$2; exit}" | tr -d " ")"
  min_final="$(tac "$OUTLOG" | awk "/^off[0-9]+:/{print}" | awk -F"final=" "{print \$2}" | awk "{print \$1}" | sort -n | head -n 1)"

  # If min_final didn’t parse (rare), set to 0
  min_final="${min_final:-0}"

  score="$(python - <<PY
min_final=float("$min_final") if "$min_final" else 0.0
avg_final=float("$avg_final") if "$avg_final" else 0.0
worst_dd=float("$worst_dd") if "$worst_dd" else 0.0
score = min_final + 0.25*avg_final - 0.75*worst_dd
print(round(score, 2))
PY
)"

  echo "$RUNTS,$(printf "%q" "$label"),$DAYS,$(printf "%q" "$OFFSETS"),${pass_count:-0},${offset_count:-0},${avg_final:-0},${worst_dd:-0},${min_final:-0},$score" >> "$OUTCSV"

done < "$CONFIG_FILE"

notify_all_done

echo
echo "Top 15 by score:"
tail -n +2 "$OUTCSV" | sort -t, -k10,10nr | head -n 15
echo
echo "Saved: $OUTCSV"
