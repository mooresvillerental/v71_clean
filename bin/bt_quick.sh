#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

# Usage examples:
#   ./bin/bt_quick.sh "CPP_v1+MACRO fee40/slip20 RESUME_540_810" "540 810"
#   ./bin/bt_quick.sh "CPP_v1+MACRO fee40/slip20 ALL" "0 270 540 810"

NAME="${1:-CPP_v1+MACRO fee40/slip20}"
OFFSETS="${2:-0 270 540 810}"

echo "Running: $NAME"
echo "Offsets: $OFFSETS"
echo ""

run_one () {
  local OFF="$1"
  echo ""
  echo "=================================================="
  echo "CPP_v1+MACRO | 90d off${OFF} | fee40/slip20"
  echo "=================================================="
  python bin/backtest_v2_engine.py --days 90 --offset-days "$OFF" --data-source binanceus \
    --fee-bps 40 --slip-bps 20 \
    --macro-mode --macro-ema-len 200 --macro-symbol BTC-USD \
    --rsi-buy 38 --rsi-sell 60 --trade-pct 0.50 \
    --dd-cap-pct 12 --soft1-pct 4 --soft2-pct 8 --soft3-pct 10 \
    --m1 0.50 --m2 0.25 --m3 0.10 \
    --cooldown-bars 4 --cooldown-loss-bars 12 \
    --trade-pct-dyn --trade-pct-lo 0.30 --trade-pct-switch-dd 3
}

for OFF in $OFFSETS; do
  run_one "$OFF"
done

./alert_done.sh || true
