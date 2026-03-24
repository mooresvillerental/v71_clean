#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

RSI_BUY="${1:-45}"
RSI_SELL="${2:-55}"
FEE_BPS="${3:-10}"
SLIP_BPS="${4:-5}"

TMPBASE="${TMPDIR:-/data/data/com.termux/files/usr/tmp}"
mkdir -p "$TMPBASE"

echo "== EZTrader Dual Backtest =="
echo "RSI buy/sell: $RSI_BUY / $RSI_SELL    fee_bps: $FEE_BPS    slip_bps: $SLIP_BPS"
echo

run_one () {
  local label="$1"; shift
  echo "---- $label ----"
  python bin/backtest_90d_v1.py \
    --rsi-buy "$RSI_BUY" --rsi-sell "$RSI_SELL" \
    --fee-bps "$FEE_BPS" --slip-bps "$SLIP_BPS" \
    "$@" | tee "$TMPBASE/ez_${label}.log"

  OUT="$(python bin/make_equity_trade_html_plotly_v1.py | tail -n 1)"
  echo "CHART: $OUT"
  echo
}

run_one "TREND"                 # trend filter ON (default)
run_one "MEAN_REV" --no-trend   # trend filter OFF

echo "DONE ✅"
