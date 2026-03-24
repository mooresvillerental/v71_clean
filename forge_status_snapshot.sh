#!/data/data/com.termux/files/usr/bin/bash
set -e
echo "=== NOW ==="
date
echo

echo "=== PWD ==="
pwd
echo

echo "=== PYTHON PROCESSES ==="
pgrep -af python || true
echo

echo "=== TOP-LEVEL FILES ==="
ls -la | sed -n '1,200p'
echo

echo "=== BIN FILES ==="
ls -la bin 2>/dev/null || true
echo

echo "=== CANDIDATE ENTRYPOINTS (top 30) ==="
find . -maxdepth 2 -type f -name "*.py" -printf "%p\n" 2>/dev/null | sed -n '1,30p'
echo

echo "=== FEATURE SCAN (matches) ==="
grep -RIn --exclude-dir=.git -E \
"place_order|create_order|submit.*order|order_id|filled|partial|remaining|ack|cooldown|killswitch|kill_switch|HALT|STOP_TRADING|daily|max_daily|day_loss|loss_limit|drawdown.*day|termux-tts|tts-speak|suggested|suppress.*sell|insufficient.*btc|websocket|wss://|subscribe|poll|while True|logging\.basicConfig|FileHandler|LOG_FILE|app_state\.json|sync_state_balances" . 2>/dev/null | sed -n '1,240p' || true
echo

echo "=== STATE FILE QUICK CHECK (common locations) ==="
for p in \
"/data/data/com.termux/files/home/v71_app_data/app_state.json" \
"./v71_app_data/app_state.json" \
"./app_state.json"
do
  if [ -f "$p" ]; then
    echo "--- Found: $p"
    python - <<PY
import json
p="$p"
st=json.load(open(p))
print("top_keys:", sorted(st.keys()))
print("cash_usd:", st.get("cash_usd"))
h=st.get("holdings",{})
print("holdings_type:", type(h).__name__)
if isinstance(h, dict):
    ks=list(h.keys())
    print("holdings_keys_sample:", ks[:10], "total:", len(ks))
PY
  fi
done
echo

echo "=== DONE ==="
