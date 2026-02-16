#!/usr/bin/env bash
set -euo pipefail

# Helper script to create a venv, install backend requirements, start the server,
# and run a couple of example requests. Useful for local manual testing.

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
VENV_DIR="$ROOT_DIR/.venv"

echo "Setting up virtualenv at $VENV_DIR"
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip setuptools wheel

if [ -f "$ROOT_DIR/backend/requirements.txt" ]; then
  echo "Installing backend/requirements.txt (this may take a while)"
  pip install -r "$ROOT_DIR/backend/requirements.txt"
else
  echo "No backend/requirements.txt found; installing minimal deps for quick testing"
  pip install -r "$ROOT_DIR/backend/requirements-ci.txt"
fi

echo "Starting uvicorn (app.main:app) on port 8000"
uvicorn app.main:app --host 127.0.0.1 --port 8000 &
PID=$!
echo "uvicorn pid=$PID"

echo "Waiting a moment for server to start..."
sleep 1

echo "Running example POST request"
curl -sS -X POST "http://127.0.0.1:8000/chatbot/" -H "Content-Type: application/json" -d '{"session_id":"local-1","user_input":"I like design and data"}' | jq . || true

echo "Health check:"
curl -sS http://127.0.0.1:8000/health | jq . || true

echo "Server is running in background (pid=$PID). To stop: kill $PID"
