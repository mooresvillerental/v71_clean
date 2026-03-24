#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/v70_host"

preset="${1:-}"
if [ -z "$preset" ]; then
  echo "Usage: ./APPLY_PRESET.sh <preset_name>"
  echo
  ./LIST_PRESETS.sh || true
  exit 1
fi

mf="presets/manifest.tsv"
desc=""
if [ -f "$mf" ]; then
  desc="$(awk -F'\t' -v p="$preset" 'BEGIN{d=""} $1==p {d=$2} END{print d}' "$mf" 2>/dev/null || true)"
fi

# Map preset -> file
file=""
if [ -f "presets/${preset}.env" ]; then
  file="presets/${preset}.env"
elif [ -f "presets/v1_${preset}.env" ]; then
  file="presets/v1_${preset}.env"
else
  # try newest matching v1_balanced_*.env style
  newest="$(ls -1 "presets/${preset}_"*.env 2>/dev/null | tail -n 1 || true)"
  [ -n "${newest:-}" ] && file="$newest"
fi

if [ -z "${file:-}" ] || [ ! -f "$file" ]; then
  echo "ERROR: preset file not found for '$preset'"
  echo "Looked for: presets/${preset}.env, presets/v1_${preset}.env, presets/${preset}_*.env"
  echo
  ./LIST_PRESETS.sh || true
  exit 1
fi

# snapshot before
before="$(python - <<'PY'
import os, re, json, pathlib
p=pathlib.Path(os.path.expanduser("~/v70_host/alerts.env"))
d={}
if p.exists():
  for ln in p.read_text().splitlines():
    ln=ln.strip()
    if not ln or ln.startswith("#"): continue
    if "=" not in ln: continue
    k,v=ln.split("=",1)
    k=k.strip()
    v=v.strip()
    # keep simple; treat as string
    d[k]=v
print(json.dumps(d, sort_keys=True))
PY
)"

ts="$(date +%Y%m%d_%H%M%S)"
cp -f alerts.env "alerts.env.bak_preset_${preset}_${ts}" 2>/dev/null || true

# apply file -> alerts.env
cp -f "$file" alerts.env

# ensure PRESET_NAME is set to current preset
if [ -f ./ALERTS_SET.sh ]; then
  ./ALERTS_SET.sh PRESET_NAME "$preset" >/dev/null 2>&1 || true
else
  # fallback: append if missing
  grep -q '^PRESET_NAME=' alerts.env 2>/dev/null || echo "PRESET_NAME=$preset" >> alerts.env
fi

# normalize if available
./NORMALIZE_ALERTS_ENV.sh >/dev/null 2>&1 || true

# snapshot after + diff
python - <<'PY'
import os, json, pathlib
before=json.loads(os.environ.get("BEFORE_JSON","{}"))
p=pathlib.Path(os.path.expanduser("~/v70_host/alerts.env"))
after={}
if p.exists():
  for ln in p.read_text().splitlines():
    ln=ln.strip()
    if not ln or ln.startswith("#"): continue
    if "=" not in ln: continue
    k,v=ln.split("=",1)
    after[k.strip()]=v.strip()

changed=[]
for k in sorted(set(before.keys())|set(after.keys())):
  if before.get(k) != after.get(k):
    changed.append((k, before.get(k,""), after.get(k,"")))

print("OK: applied preset:", os.environ.get("PRESET_NAME",""))
desc=os.environ.get("PRESET_DESC","")
if desc:
  print("Intent:", desc)

if not changed:
  print("Changed: (none)")
else:
  print("Changed:")
  for k,b,a in changed:
    # keep output compact
    if len(b)>28: b=b[:28]+"…"
    if len(a)>28: a=a[:28]+"…"
    print(f" - {k}: {b} -> {a}")
PY
