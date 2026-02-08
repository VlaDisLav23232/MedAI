#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$ROOT/.medai_pids"

echo "=== MedAI Services Status ==="
echo

# Check backend port 8000
BACKEND_PID=$(ss -tlnp 2>/dev/null | grep -oP ':8000.*pid=\K[0-9]+' | head -1 || echo "")
if [[ -n "$BACKEND_PID" ]]; then
  echo "✓ Backend: RUNNING (PID $BACKEND_PID, port 8000)"
  echo "  URL: http://localhost:8000"
  echo "  Docs: http://localhost:8000/docs"
else
  echo "✗ Backend: NOT RUNNING"
fi

echo

# Check frontend port 3000
FRONTEND_PID=$(ss -tlnp 2>/dev/null | grep -oP ':3000.*pid=\K[0-9]+' | head -1 || echo "")
if [[ -n "$FRONTEND_PID" ]]; then
  echo "✓ Frontend: RUNNING (PID $FRONTEND_PID, port 3000)"
  echo "  URL: http://localhost:3000"
else
  echo "✗ Frontend: NOT RUNNING"
fi

echo

# Check logs
if [[ -f "$ROOT/medai-logs/backend.log" ]]; then
  BACKEND_LOG_SIZE=$(wc -l < "$ROOT/medai-logs/backend.log")
  echo "📋 Backend log: $BACKEND_LOG_SIZE lines (medai-logs/backend.log)"
fi

if [[ -f "$ROOT/medai-logs/frontend.log" ]]; then
  FRONTEND_LOG_SIZE=$(wc -l < "$ROOT/medai-logs/frontend.log")
  echo "📋 Frontend log: $FRONTEND_LOG_SIZE lines (medai-logs/frontend.log)"
fi

echo
