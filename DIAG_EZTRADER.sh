#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

echo "=== Restarting server cleanly ==="
./stop_server.sh >/dev/null 2>&1 || true
./start_server.sh

echo
echo "=== Quick API checks ==="
echo "[health]"; curl -sS http://127.0.0.1:8080/health ; echo
echo "[signal]"; curl -sS http://127.0.0.1:8080/signal ; echo
echo "[reco]";   curl -sS http://127.0.0.1:8080/reco   ; echo

echo
URL="http://127.0.0.1:8080/trade?ts=$(date +%s)"
echo "OPEN THIS (new session): $URL"
