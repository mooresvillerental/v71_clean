#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

PORT=18092
cd "$HOME/v71_clean"

export V70_HOST=127.0.0.1
export V70_PORT="$PORT"
export PYTHONPATH=.

# v71 isolated data dirs
export EZ_ENGINE_DATA_DIR="$HOME/v71_engine_data"
export EZ_APP_DATA_DIR="$HOME/v71_app_data"
export EZ_ENGINE_STATE_PATH="$HOME/v71_engine_data/state.json"
export EZ_APP_STATE_PATH="$HOME/v71_app_data/state.json"
export EZ_CONFIRM_PATH="$HOME/v71_app_data/confirm.json"

nohup python -m app.server >"$HOME/ez_v71_server.log" 2>&1 &
sleep 0.9

# Let bash expand $PORT before Python runs
python - <<PY2
import urllib.request, json
print(json.loads(urllib.request.urlopen("http://127.0.0.1:$PORT/health?ts=1", timeout=6).read().decode()))
print("LINK: http://127.0.0.1:$PORT/ui/trade.html?ts=1")
PY2
