#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
cd ~/v70_host
./stop_server.sh 2>/dev/null || true
./start_server.sh
termux-open-url "http://127.0.0.1:8080/trade?ts=$(date +%s)"
