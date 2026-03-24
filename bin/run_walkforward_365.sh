#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

DAYS=365
SRC=binanceus

# NOTE:
# - This script only *runs* backtests; it does not modify any python.
# - Keep filters OUT unless you are explicitly testing them.

BASE_ARGS="--days $DAYS --data-source $SRC \
  --rsi-buy 38 --rsi-sell 60 \
  --trade-pct 0.50 --fee-bps 10 --slip-bps 5 \
  --dd-cap-pct 20 --soft1-pct 7 --soft2-pct 12 --soft3-pct 16 \
  --m1 0.60 --m2 0.35 --m3 0.18 \
  --cooldown-bars 4 --cooldown-loss-bars 12"

OFFSETS=(0 365 730 1095 1460)

echo "offset_days,final_equity,max_dd,trades,winrate"
for OFF in "${OFFSETS[@]}"; do
  OUT=$(python bin/backtest_90d_v1.py --offset-days "$OFF" $BASE_ARGS | tail -n 40)

  FE=$(echo "$OUT" | awk '/final_equity:/ {print $2}' | tail -n 1)
  DD=$(echo "$OUT" | awk '/max_drawdown_usd:/ {print $2}' | tail -n 1)
  TR=$(echo "$OUT" | awk '/trades_total:/ {print $2}' | tail -n 1)
  WR=$(echo "$OUT" | awk '/winrate%:/ {print $NF}' | tail -n 1)

  echo "$OFF,$FE,$DD,$TR,$WR"
done
