#!/data/data/com.termux/files/usr/bin/bash
# Usage: ./alert_done.sh <exit_code> <seconds> <label> <equity> <dd>
code="${1:-0}"
secs="${2:-0}"
label="${3:-Backtest}"
equity="${4:-unknown}"
dd="${5:-unknown}"

# format runtime
h=$((secs/3600)); m=$(((secs%3600)/60)); s=$((secs%60))
rt=""
if [ "$h" -gt 0 ]; then rt="${h}h ${m}m ${s}s"; elif [ "$m" -gt 0 ]; then rt="${m}m ${s}s"; else rt="${s}s"; fi

if [ "$code" -eq 0 ]; then
  msg="${label} complete. Runtime ${rt}. Final equity ${equity}. Max drawdown ${dd}."
  termux-tts-speak "$msg" >/dev/null 2>&1 || true
  termux-notification --title "Backtest Done ✅" --content "$msg" >/dev/null 2>&1 || true
else
  msg="${label} FAILED. Runtime ${rt}. Exit code ${code}."
  termux-tts-speak "$msg" >/dev/null 2>&1 || true
  termux-notification --title "Backtest Failed ❌" --content "$msg" >/dev/null 2>&1 || true
fi
