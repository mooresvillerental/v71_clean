from pathlib import Path
import re

p = Path("bin/bt_gate_and_promote.sh")
s = p.read_text()

MARK = "### FORGE_NOTIFY_V1"
if MARK in s:
    print("Already patched:", p)
    raise SystemExit(0)

helper = r'''
### FORGE_NOTIFY_V1
notify_done() {
  local status="$1"
  local msg="Gate ${status}: ${LABEL} ${DAYS}d | pass ${pass_count}/${offset_count} | avg ${avg_final} | worstDD ${worst_dd}"

  echo ""
  echo "=== ${msg} ==="

  # Android notification
  if command -v termux-notification >/dev/null 2>&1; then
    termux-notification --title "EZTrader Gate ${status}" --content "${msg}" --priority high >/dev/null 2>&1 || true
  fi

  # Speak details
  if command -v termux-tts-speak >/dev/null 2>&1; then
    termux-tts-speak "${msg}" >/dev/null 2>&1 || true
  fi

  # Terminal beep x3
  for _ in 1 2 3; do printf "\a"; sleep 1; done
}
'''

# Insert helper right after: set -euo pipefail
s2, n = re.subn(r'^(set -euo pipefail\s*)$',
               r'\1' + helper,
               s,
               count=1,
               flags=re.M)
if n != 1:
    raise SystemExit("Could not find 'set -euo pipefail' to insert helper.")

# Ensure we notify on FAIL before exit
s2, nfail = re.subn(r'echo "ROBUST_GATE: FAIL"\s*\n\s*exit 1',
                    'echo "ROBUST_GATE: FAIL"\nnotify_done "FAIL"\nexit 1',
                    s2,
                    count=1)

# Ensure we notify on PASS (before promotion)
s2, npass = re.subn(r'echo "ROBUST_GATE: PASS"\s*',
                    'echo "ROBUST_GATE: PASS"\nnotify_done "PASS"\n',
                    s2,
                    count=1)

if nfail != 1 or npass != 1:
    raise SystemExit(f"Patch points not found (FAIL={nfail}, PASS={npass}). Not patching.")

p.write_text(s2)
print("Patched:", p)
