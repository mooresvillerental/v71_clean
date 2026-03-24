#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

BASE="http://127.0.0.1:8080"
INTERVAL="${1:-10}"   # seconds

# Try a few likely endpoints until one returns JSON
ENDPOINTS=(
  "/opportunities"
  "/opps"
  "/top"
  "/api/opportunities"
  "/api/opps"
  "/signals"
)

pick_endpoint() {
  for ep in "${ENDPOINTS[@]}"; do
    out="$(curl -s --max-time 2 "${BASE}${ep}" || true)"
    # must look like JSON and contain something useful
    python - <<PY >/dev/null 2>&1 || continue
import json
s = """$out""".strip()
j = json.loads(s)
# accept dict or list, but must contain any of these keys somewhere
txt = s.lower()
ok = ("symbol" in txt) or ("side" in txt) or ("signal" in txt) or ("btc" in txt)
raise SystemExit(0 if ok else 2)
PY
    echo "$ep"
    return 0
  done
  echo ""
  return 1
}

EP="$(pick_endpoint || true)"
if [ -z "$EP" ]; then
  echo "Could not find a JSON opportunities/signals endpoint on ${BASE}."
  echo "Run: curl -s ${BASE}/ | head"
  echo "Then tell me what paths you see (or paste last ~30 lines)."
  exit 1
fi

echo "Using endpoint: ${BASE}${EP}"
echo "Polling every ${INTERVAL}s ..."
echo ""

say() {
  local msg="$1"
  if command -v termux-tts-speak >/dev/null 2>&1; then
    termux-tts-speak "$msg" >/dev/null 2>&1 || true
  fi
}

last_sig=""

while true; do
  j="$(curl -s --max-time 3 "${BASE}${EP}" || true)"
  if [ -z "$j" ]; then
    echo "No response. Is server up? ${BASE}/health"
    sleep "$INTERVAL"
    continue
  fi

  # Print a compact “best effort” summary without knowing exact schema
  summary="$(python - <<PY 2>/dev/null || true
import json, re
s = """$j""".strip()
obj = json.loads(s)

def pick(d, keys):
  for k in keys:
    if isinstance(d, dict) and k in d: return d[k]
  return None

# If list, try first item
top = obj[0] if isinstance(obj, list) and obj else obj

sym = pick(top, ["symbol","sym","pair","ticker"]) or "BTC-USD"
side = pick(top, ["side","signal","action"]) or pick(top, ["recommendation","reco"]) or "HOLD"
price = pick(top, ["price","last","px"]) 
rsi = pick(top, ["rsi","RSI"])
usd = pick(top, ["usd","usd_amount","buy_usd","suggest_usd"])
btc = pick(top, ["btc","btc_amount","sell_btc","suggest_btc"])

def fmt(x):
  if x is None: return ""
  try:
    if isinstance(x, (int,float)): return f"{x:.6g}"
  except: pass
  return str(x)

parts = [f"{sym}", f"{side}"]
if price is not None: parts.append(f"px={fmt(price)}")
if rsi is not None: parts.append(f"rsi={fmt(rsi)}")
if usd is not None: parts.append(f"usd={fmt(usd)}")
if btc is not None: parts.append(f"btc={fmt(btc)}")

print(" | ".join(parts))
PY
)"
  if [ -z "$summary" ]; then
    # fallback: just show first 1 line of JSON
    summary="$(echo "$j" | head -n 1 | cut -c1-200)"
  fi

  # trigger speech only when the summary changes AND contains BUY/SELL
  sig_key="$(echo "$summary" | tr "[:lower:]" "[:upper:]")"
  if [ "$sig_key" != "$last_sig" ]; then
    echo "$(date +%H:%M:%S)  $summary"
    if echo "$sig_key" | grep -Eq "BUY|SELL"; then
      say "$summary"
    fi
    last_sig="$sig_key"
  fi

  sleep "$INTERVAL"
done
