#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8080}"
SYMBOL="${SYMBOL:-BTC-USD}"
POLL_SEC="${POLL_SEC:-5}"

LOG_TS(){ date "+%Y-%m-%d %H:%M:%S"; }

curl_json(){
  # Prints JSON or {} on any error/timeout
  curl -sS --max-time 4 "$1" 2>/dev/null || echo "{}"
}

pyget(){
  # Usage: pyget "<json>" "<keypath>" "<default>"
  # keypath examples:
  #   signal.action
  #   signal.price
  #   settings.reco_percent
  python - "$2" "$3" <<'PY'
import json, sys
keypath = sys.argv[1]
default = sys.argv[2]
raw = sys.stdin.read().strip()
try:
    obj = json.loads(raw) if raw else {}
except Exception:
    obj = {}
cur = obj
try:
    for k in keypath.split("."):
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            cur = None
            break
except Exception:
    cur = None
if cur is None:
    print(default)
else:
    if isinstance(cur, (dict, list)):
        print(json.dumps(cur))
    else:
        print(cur)
PY
}

has_cmd(){ command -v "$1" >/dev/null 2>&1; }

speak(){
  local msg="$1"
  if has_cmd termux-tts-speak; then
    termux-tts-speak "$msg" >/dev/null 2>&1 || true
  fi
}

notify(){
  local title="$1"
  local msg="$2"
  if has_cmd termux-notification; then
    termux-notification --title "$title" --content "$msg" >/dev/null 2>&1 || true
  fi
}

last_action=""

echo "[$(LOG_TS)] live_watch_btc starting BASE_URL=$BASE_URL SYMBOL=$SYMBOL POLL_SEC=$POLL_SEC"

while true; do
  sig_json="$(curl_json "$BASE_URL/signal?symbol=$SYMBOL")"
  set_json="$(curl_json "$BASE_URL/settings")"
  port_json="$(curl_json "$BASE_URL/portfolio")"

  action="$(printf "%s" "$sig_json" | pyget "signal.action" "HOLD")"
  reason="$(printf "%s" "$sig_json" | pyget "signal.reason" "-")"
  price="$(printf "%s" "$sig_json" | pyget "signal.price" "0")"

  cash="$(printf "%s" "$port_json" | pyget "cash_usd" "0")"
  qty="$(printf "%s" "$port_json" | pyget "holdings_qty.$SYMBOL" "0")"

  reco_mode="$(printf "%s" "$set_json" | pyget "settings.reco_mode" "percent")"
  reco_pct="$(printf "%s" "$set_json" | pyget "settings.reco_percent" "0.05")"
  min_trade_usd="$(printf "%s" "$set_json" | pyget "settings.min_trade_usd" "25")"

  # sanitize numeric
  python - <<PY >/dev/null 2>&1 || true
float("$price"); float("$cash"); float("$qty"); float("$reco_pct"); float("$min_trade_usd")
PY

  # defaults if parse weird
  price="${price:-0}"; cash="${cash:-0}"; qty="${qty:-0}"
  reco_pct="${reco_pct:-0.05}"; min_trade_usd="${min_trade_usd:-25}"

  # Recommended amounts (simple + safe)
  usd="0"
  btc="0"
  if [ "$action" = "BUY" ]; then
    usd="$(python - <<PY
p=float("$price") if float("$price")>0 else 0.0
cash=float("$cash")
pct=float("$reco_pct")
m=float("$min_trade_usd")
amt=max(0.0, cash*pct)
if amt < m: amt = 0.0
print(f"{amt:.2f}")
PY
)"
    btc="$(python - <<PY
p=float("$price") if float("$price")>0 else 0.0
usd=float("$usd")
print(f"{(usd/p) if p>0 else 0.0:.8f}")
PY
)"
  elif [ "$action" = "SELL" ]; then
    btc="$(python - <<PY
q=float("$qty")
pct=float("$reco_pct")
amt=max(0.0, q*pct)
print(f"{amt:.8f}")
PY
)"
    usd="$(python - <<PY
p=float("$price") if float("$price")>0 else 0.0
btc=float("$btc")
print(f"{btc*p:.2f}")
PY
)"
  fi

  line="[$(LOG_TS)] $SYMBOL action=$action price=$price cash=$cash qty=$qty reco=${usd}USD/${btc}BTC reason=$reason"
  echo "$line"

  # Alert only when action changes (or first non-empty)
  if [ "$action" != "$last_action" ]; then
    last_action="$action"
    msg="$SYMBOL $action. Price $price. Reco $usd dollars ($btc BTC). Reason: $reason"
    notify "EZTrader Signal" "$msg"
    speak "$msg"
  fi

  sleep "$POLL_SEC"
done
