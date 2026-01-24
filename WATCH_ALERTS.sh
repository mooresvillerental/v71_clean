#!/usr/bin/env bash
set -euo pipefail

export PATH="${PREFIX:-/data/data/com.termux/files/usr}/bin:/data/data/com.termux/files/usr/bin:$PATH"

BASE_URL="${BASE_URL:-http://127.0.0.1:8080}"
ENV_FILE="${ENV_FILE:-$HOME/v70_host/alerts.env}"
LOG="${LOG:-$HOME/v70_host/logs/watch_alerts.log}"
STATE_DIR="${STATE_DIR:-$HOME/v70_host/.alerts_state}"
PRICE_STATE="${PRICE_STATE:-$STATE_DIR/price_move.json}"

mkdir -p "$(dirname "$LOG")" "$STATE_DIR" >/dev/null 2>&1 || true

logline(){ printf "%s | %s\n" "$(date '+%Y-%m-%d %H:%M:%S')" "$1" >> "$LOG" 2>/dev/null || true; }

# Load cfg each loop so changes apply immediately.
load_cfg(){
  # sane defaults (battery-aware)
  ALERTS_ENABLED="${ALERTS_ENABLED:-1}"
  POLL_SEC="${POLL_SEC:-10}"
  REPEAT_SEC="${REPEAT_SEC:-0}"
  CURL_MAX_TIME="${CURL_MAX_TIME:-3}"
  STOP_ON_CONFIRM="${STOP_ON_CONFIRM:-1}"

  SPEAK="${SPEAK:-0}"
  NOTIFY="${NOTIFY:-1}"
  VIBRATE="${VIBRATE:-1}"

  QUIET_ENABLED="${QUIET_ENABLED:-1}"
  QUIET_START="${QUIET_START:-22:00}"
  QUIET_END="${QUIET_END:-07:00}"
  QUIET_ALLOW_NOTIFY="${QUIET_ALLOW_NOTIFY:-0}"
  QUIET_ALLOW_VIBRATE="${QUIET_ALLOW_VIBRATE:-0}"
  QUIET_ALLOW_SPEAK="${QUIET_ALLOW_SPEAK:-0}"

  PRICE_MOVE_ENABLED="${PRICE_MOVE_ENABLED:-0}"
  PRICE_MOVE_THRESHOLD_PCT="${PRICE_MOVE_THRESHOLD_PCT:-5}"
  PRICE_MOVE_WINDOW_MIN="${PRICE_MOVE_WINDOW_MIN:-60}"
  PRICE_MOVE_DIRECTION="${PRICE_MOVE_DIRECTION:-both}"
  PRICE_MOVE_OVERRIDE_QUIET="${PRICE_MOVE_OVERRIDE_QUIET:-0}"

  WAKE_TRADE_ENABLED="${WAKE_TRADE_ENABLED:-0}"
  WAKE_TRADE_MIN_USD="${WAKE_TRADE_MIN_USD:-150}"
  WAKE_TRADE_OVERRIDE_QUIET="${WAKE_TRADE_OVERRIDE_QUIET:-0}"

  VIBRATE_MS="${VIBRATE_MS:-800}"
  VIBRATE_BUY="${VIBRATE_BUY:-120,120,120}"
  VIBRATE_SELL="${VIBRATE_SELL:-500,180,500}"

  if [ -f "$ENV_FILE" ]; then
    set +u
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set -u
  fi
}

# "HH:MM" -> minutes since midnight
hhmm_to_min(){ python - "$1" <<'PY'
import sys
h,m=sys.argv[1].strip().split(":")
print(int(h)*60+int(m))
PY
}

in_quiet_hours(){
  local now_hm now_min s_min e_min
  now_hm="$(date '+%H:%M')"
  now_min="$(hhmm_to_min "$now_hm")"
  s_min="$(hhmm_to_min "$QUIET_START")"
  e_min="$(hhmm_to_min "$QUIET_END")"

  if [ "$s_min" -le "$e_min" ]; then
    [ "$now_min" -ge "$s_min" ] && [ "$now_min" -lt "$e_min" ]
  else
    [ "$now_min" -ge "$s_min" ] || [ "$now_min" -lt "$e_min" ]
  fi
}

# JSON helpers (top-level + nested)
jget(){ python - "$1" <<'PY'
import sys, json
k=sys.argv[1]
try:
  o=json.loads(sys.stdin.read() or "{}")
  v=o.get(k,"")
  if v is None: v=""
  if isinstance(v,(dict,list)): print("")
  else: print(v)
except Exception:
  print("")
PY
}
jgetp(){ python - "$@" <<'PY'
import sys, json
keys=sys.argv[1:]
try:
  o=json.loads(sys.stdin.read() or "{}")
  cur=o
  for k in keys:
    if not isinstance(cur, dict):
      print(""); raise SystemExit
    cur=cur.get(k)
  if cur is None: cur=""
  if isinstance(cur,(dict,list)): print("")
  else: print(cur)
except SystemExit:
  pass
except Exception:
  print("")
PY
}

# price move detector: keeps a tiny list of (ts, price) in PRICE_STATE
price_move_triggered(){
  # args: current_price
  python - "$PRICE_STATE" "$1" "$PRICE_MOVE_WINDOW_MIN" "$PRICE_MOVE_THRESHOLD_PCT" "$PRICE_MOVE_DIRECTION" <<'PY'
import sys, json, time, math
path=sys.argv[1]
try: price=float(sys.argv[2])
except: 
  print("0"); raise SystemExit
win_min=float(sys.argv[3] or 60)
thr=float(sys.argv[4] or 5)
direction=(sys.argv[5] or "both").lower().strip()

now=int(time.time())
cut=now-int(win_min*60)

state={"pts":[],"last_fire":0}
try:
  state=json.loads(open(path,"r").read() or "{}")
except: 
  pass
pts=state.get("pts") or []
# prune
pts=[p for p in pts if isinstance(p,list) and len(p)==2 and isinstance(p[0],int) and p[0]>=cut]
pts.append([now, price])

# compute pct move from earliest to latest in window
fire=0
if len(pts)>=2:
  p0=pts[0][1]
  p1=pts[-1][1]
  if p0 and p0>0:
    pct=(p1-p0)/p0*100.0
    if direction=="up":
      fire = 1 if pct>=thr else 0
    elif direction=="down":
      fire = 1 if pct<=-thr else 0
    else:
      fire = 1 if abs(pct)>=thr else 0

state["pts"]=pts[-500:]  # hard cap
# avoid firing every loop: only allow new fire after window/4 seconds
cooldown=max(30, int(win_min*60/4))
last=int(state.get("last_fire") or 0)
if fire and (now-last) < cooldown:
  fire=0
if fire:
  state["last_fire"]=now

try:
  with open(path,"w") as f:
    f.write(json.dumps(state))
except:
  pass

print("1" if fire else "0")
PY
}

say(){
  local msg="$1"
  logline "$msg"

  local do_notify="$NOTIFY"
  local do_speak="$SPEAK"

  if [ "$QUIET_ENABLED" = "1" ] && in_quiet_hours; then
    [ "$QUIET_ALLOW_NOTIFY" = "1" ] || do_notify="0"
    [ "$QUIET_ALLOW_SPEAK" = "1" ] || do_speak="0"
  fi

  if [ "$do_notify" = "1" ]; then
    termux-notification --title "EZTrader" --content "$msg" --priority high >/dev/null 2>&1 || true
  fi
  if [ "$do_speak" = "1" ]; then
    termux-tts-speak "$msg" >/dev/null 2>&1 || true
  fi
}

buzz(){
  local action="${1:-}"
  local do_vibrate="$VIBRATE"

  if [ "$QUIET_ENABLED" = "1" ] && in_quiet_hours; then
    [ "$QUIET_ALLOW_VIBRATE" = "1" ] || do_vibrate="0"
  fi
  [ "$do_vibrate" = "1" ] || return 0
  [ "${VIBRATE_MS}" != "0" ] || return 0

  if [ "$action" = "BUY" ] && [ -n "${VIBRATE_BUY}" ]; then
    termux-vibrate -p "${VIBRATE_BUY}" >/dev/null 2>&1 || true
  elif [ "$action" = "SELL" ] && [ -n "${VIBRATE_SELL}" ]; then
    termux-vibrate -p "${VIBRATE_SELL}" >/dev/null 2>&1 || true
  else
    termux-vibrate -d "${VIBRATE_MS}" >/dev/null 2>&1 || true
  fi
}

termux-wake-lock >/dev/null 2>&1 || true

last_key=""
last_repeat_ts=0
last_confirmed_at=""

load_cfg
say "EZTrader alerts running. Poll=${POLL_SEC}s Repeat=${REPEAT_SEC}s Speak=${SPEAK} Notify=${NOTIFY} Vibrate=${VIBRATE} Quiet=${QUIET_ENABLED} ${QUIET_START}-${QUIET_END}"

while true; do
  load_cfg

  if [ "${ALERTS_ENABLED}" != "1" ]; then
    sleep "$POLL_SEC"
    continue
  fi

  # stop-on-confirm: if confirm changes, exit (prevents nagging)
  if [ "$STOP_ON_CONFIRM" = "1" ]; then
    cj="$(curl -m "$CURL_MAX_TIME" -sS "$BASE_URL/confirm/status?ts=$(date +%s)" 2>/dev/null || true)"
    ca="$(printf '%s' "$cj" | jgetp confirm confirmed_at)"
    if [ -n "${ca}" ] && [ "$ca" != "$last_confirmed_at" ]; then
      if [ -z "$last_confirmed_at" ]; then
        last_confirmed_at="$ca"
      else
        say "EZTrader: confirm detected ($ca). Alerts stopping."
        exit 0
      fi
    fi
  fi

  j="$(curl -m "$CURL_MAX_TIME" -sS "$BASE_URL/reco?ts=$(date +%s)" 2>/dev/null || true)"
  ok="$(printf '%s' "$j" | jget ok)"
  action="$(printf '%s' "$j" | jget action | tr '[:lower:]' '[:upper:]')"
  symbol="$(printf '%s' "$j" | jget symbol)"
  price="$(printf '%s' "$j" | jget price)"
  rec_usd="$(printf '%s' "$j" | jget recommended_usd)"
  now_ts="$(date +%s)"

  if [ "$ok" != "True" ] && [ "$ok" != "true" ]; then
    last_key=""; last_repeat_ts=0
    sleep "$POLL_SEC"; continue
  fi
  if [ "$action" != "BUY" ] && [ "$action" != "SELL" ]; then
    last_key=""; last_repeat_ts=0
    sleep "$POLL_SEC"; continue
  fi

  # amount normalize
  amt="$(python - <<PY
import math
try:
  x=float("$rec_usd")
  if math.isfinite(x) and x>0: print(f"{x:.2f}")
  else: print("")
except: print("")
PY
)"

  # Battery + sanity: key excludes price so we don't "change" every loop from tiny price movement
  key="${action}|${symbol}|${amt}"

  # QUIET OVERRIDE DECISION:
  # If quiet is active AND base quiet would silence, allow wake if:
  #   - price move trigger AND override enabled
  #   - wake-trade trigger AND override enabled
  quiet_now=0
  if [ "$QUIET_ENABLED" = "1" ] && in_quiet_hours; then quiet_now=1; fi

  override_now=0
  if [ "$quiet_now" = "1" ]; then
    # price move override
    if [ "$PRICE_MOVE_ENABLED" = "1" ] && [ "$PRICE_MOVE_OVERRIDE_QUIET" = "1" ]; then
      pm="$(price_move_triggered "${price:-0}" || echo 0)"
      if [ "$pm" = "1" ]; then override_now=1; fi
    fi
    # wake trade override
    if [ "$WAKE_TRADE_ENABLED" = "1" ] && [ "$WAKE_TRADE_OVERRIDE_QUIET" = "1" ]; then
      python - "$amt" "$WAKE_TRADE_MIN_USD" <<'PY' >/dev/null 2>&1 && override_now=1 || true
import sys, math
try:
  a=float(sys.argv[1] or 0); m=float(sys.argv[2] or 0)
  if math.isfinite(a) and a>=m and m>0: raise SystemExit(0)
except:
  pass
raise SystemExit(1)
PY
    fi
  fi

  # Apply override: temporarily allow notify/vibrate/speak in quiet ONLY if override_now=1
  if [ "$quiet_now" = "1" ] && [ "$override_now" = "1" ]; then
    QUIET_ALLOW_NOTIFY=1
    QUIET_ALLOW_VIBRATE=1
    QUIET_ALLOW_SPEAK=1
  fi

  if [ "$key" != "$last_key" ]; then
    last_key="$key"
    last_repeat_ts="$now_ts"
    if [ -n "$amt" ]; then
      say "EZTrader ${action}. ${symbol}. Recommended ${amt} dollars."
    else
      say "EZTrader ${action}. ${symbol}."
    fi
    buzz "$action"
  else
    if [ "$REPEAT_SEC" != "0" ] && [ "$REPEAT_SEC" != "0.0" ]; then
      if [ $((now_ts - last_repeat_ts)) -ge "$REPEAT_SEC" ]; then
        last_repeat_ts="$now_ts"
        if [ -n "$amt" ]; then
          say "Reminder: ${action} still active. ${amt} dollars."
        else
          say "Reminder: ${action} still active."
        fi
        buzz "$action"
      fi
    fi
  fi

  sleep "$POLL_SEC"
done
