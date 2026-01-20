#!/data/data/com.termux/files/usr/bin/bash
set -e

cd "$HOME/v70_host"

echo "== git status (before) =="
git status --porcelain || true

echo "== rolling back to last commit =="
git reset --hard HEAD

echo "== restarting server =="
pkill -f "python -m app.server" >/dev/null 2>&1 || true
pkill -f "app/server.py" >/dev/null 2>&1 || true
./run_boring.sh

echo "== done =="
