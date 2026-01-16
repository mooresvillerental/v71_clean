#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
cd ~/v70_host || exit 1

python -m py_compile app/server.py

nohup python -m app.server > server.log 2>&1 &
echo $! > server.pid
sleep 1

curl -sS http://127.0.0.1:8080/health ; echo
