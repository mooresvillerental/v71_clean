#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

# Promotes a chosen strategy config into the APP settings so the UI/server uses it.
# This does NOT enable automation. It just makes the app reflect what you tested.
#
# Usage:
#   ./bin/promote_to_app.sh "CPP_v1+MACRO fee40/slip20"
#
# Optional env:
#   RESET_ENGINE=1   -> reset v71_engine_data/state.json to {}
#   RESTART=1        -> restart ~/v71_host stack (default 1)

NAME="${1:-CPP_v1+MACRO fee40/slip20}"
APP_SETTINGS="$HOME/v71_app_data/settings.json"
ENGINE_STATE="$HOME/v71_engine_data/state.json"

mkdir -p "$HOME/v71_app_data" "$HOME/v71_engine_data"

python - <<PY
import json, os, time
p = os.path.expanduser("$APP_SETTINGS")
try:
    st = json.load(open(p,"r"))
except Exception:
    st = {}

# Strategy profile payload (this mirrors your backtest args exactly)
profile = {
  "name": "${NAME}",
  "updated_ts": int(time.time()),
  "mode": "ADVANCED",
  "paper_enforced": False,
  "strategy": {
    "id": "CPP_v1_MACRO",
    "data_source": "binanceus",
    "fee_bps": 40,
    "slip_bps": 20,
    "macro_mode": True,
    "macro_symbol": "BTC-USD",
    "macro_ema_len": 200,

    "rsi_buy": 38,
    "rsi_sell": 60,

    "trade_pct": 0.50,
    "trade_pct_dyn": True,
    "trade_pct_lo": 0.30,
    "trade_pct_switch_dd": 3,

    "dd_cap_pct": 12,
    "soft1_pct": 4,
    "soft2_pct": 8,
    "soft3_pct": 10,
    "m1": 0.50,
    "m2": 0.25,
    "m3": 0.10,

    "cooldown_bars": 4,
    "cooldown_loss_bars": 12,
    "trend_filter": False
  }
}

# Store under a stable key; keep anything else already in settings.json
st.setdefault("profiles", {})
st["profiles"]["active"] = profile
st["active_profile_name"] = "${NAME}"

os.makedirs(os.path.dirname(p), exist_ok=True)
with open(p,"w") as f:
    json.dump(st,f,indent=2,sort_keys=False)

print("WROTE:", p)
print("ACTIVE PROFILE:", st.get("active_profile_name"))
PY

if [ "${RESET_ENGINE:-0}" = "1" ]; then
  echo "{}" > "$ENGINE_STATE"
  echo "RESET ENGINE STATE: $ENGINE_STATE"
fi

if [ "${RESTART:-1}" = "1" ]; then
  if [ -x "$HOME/v71_host/stop_stack.sh" ] && [ -x "$HOME/v71_host/start_stack.sh" ]; then
    echo "Restarting v71_host stack..."
    (cd "$HOME/v71_host" && ./stop_stack.sh && ./start_stack.sh)
  else
    echo "NOTE: start/stop scripts not found in ~/v71_host. Skipping restart."
  fi
fi

echo "DONE."
echo "Health:"
curl -s --max-time 2 http://127.0.0.1:8081/health || true
echo
echo "Signal:"
curl -s --max-time 2 "http://127.0.0.1:8081/signal?symbol=BTC-USD" || true
echo
echo "Decision:"
curl -s --max-time 2 "http://127.0.0.1:8081/decision?symbol=BTC-USD" || true
echo
