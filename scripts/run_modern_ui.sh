#!/usr/bin/env bash
set -euo pipefail

if [ ! -d ".venv" ]; then
  echo "Missing .venv. Create it first: python3 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]""
  exit 1
fi

if [ ! -d "frontend/node_modules" ]; then
  echo "Installing frontend dependencies..."
  npm --prefix "frontend" install
fi

cleanup() {
  if [ -n "${API_PID:-}" ] && kill -0 "$API_PID" 2>/dev/null; then kill "$API_PID"; fi
  if [ -n "${WEB_PID:-}" ] && kill -0 "$WEB_PID" 2>/dev/null; then kill "$WEB_PID"; fi
}
trap cleanup EXIT

.venv/bin/uvicorn net.signaling_service:app --reload --port 8000 &
API_PID=$!
npm --prefix "frontend" run dev -- --host 127.0.0.1 --port 5173 &
WEB_PID=$!

wait
