#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$ROOT/.medai_pids"

if [[ -f "$PID_FILE" ]]; then
  # shellcheck disable=SC1090
  . "$PID_FILE"

  if [[ -n "${BACKEND_PID:-}" ]]; then
    echo "Stopping backend ($BACKEND_PID)"
    kill "$BACKEND_PID" 2>/dev/null || true
  fi

  if [[ -n "${FRONTEND_PID:-}" ]]; then
    echo "Stopping frontend ($FRONTEND_PID)"
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi

  rm -f "$PID_FILE"
else
  echo "No PID file found, checking ports..."
fi

# Fallback: kill any process on default ports
lsof -ti tcp:8000 | xargs -r kill -9 2>/dev/null && echo "Killed process on port 8000" || true
lsof -ti tcp:3000 | xargs -r kill -9 2>/dev/null && echo "Killed process on port 3000" || true

echo "Stopped."
