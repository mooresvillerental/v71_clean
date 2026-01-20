#!/data/data/com.termux/files/usr/bin/bash
set -e

cd "$HOME/v70_host"

FILE="ui/trade.html"

echo "== PRECHECK: $FILE =="

need1='function speak'
need2='async function fetchSignal'
need3='fetch("/reco'

c1=$(grep -c "$need1" "$FILE" || true)
c2=$(grep -c "$need2" "$FILE" || true)
c3=$(grep -c "$need3" "$FILE" || true)

echo "count: speak()           = $c1"
echo "count: fetchSignal()     = $c2"
echo "count: fetch(\"/reco\")   = $c3"

bad=0

if [ "$c1" -ne 1 ]; then echo "!! PROBLEM: speak() should appear exactly once"; bad=1; fi
if [ "$c2" -ne 1 ]; then echo "!! PROBLEM: fetchSignal() should appear exactly once"; bad=1; fi
if [ "$c3" -lt 1 ]; then echo "!! PROBLEM: UI is not calling /reco"; bad=1; fi

# quick sanity: script closure exists
if ! grep -q "</script>" "$FILE"; then echo "!! PROBLEM: missing </script> tag"; bad=1; fi

if [ "$bad" -eq 0 ]; then
  echo "OK: UI looks sane."
else
  echo "FAIL: UI check failed. Recommendation:"
  echo "  1) run: git diff ui/trade.html"
  echo "  2) if unsure, run: ./ROLLBACK_AND_RUN.sh"
  exit 1
fi
