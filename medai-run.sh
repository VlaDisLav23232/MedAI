#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: medai-run.sh [--mode MODE] [--root PATH] [--backend-port PORT] [--frontend-port PORT] [--no-reload]

Modes:
  mock      DEBUG=true (mock tools), judge off, 27B off
  real      DEBUG=false (real tools), judge on, 27B on
  fast      DEBUG=false, judge off, 27B on
  fastest   DEBUG=false, judge off, 27B off

Defaults:
  --mode mock
  --root this repo
  --backend-port 8000
  --frontend-port 3000

Examples:
  ./medai-run.sh --mode real
  ./medai-run.sh --mode fast --backend-port 8001 --frontend-port 3001
EOF
}

MODE="mock"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_PORT=8000
FRONTEND_PORT=3000
RELOAD=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)
      MODE="$2"; shift 2 ;;
    --root)
      ROOT="$2"; shift 2 ;;
    --backend-port)
      BACKEND_PORT="$2"; shift 2 ;;
    --frontend-port)
      FRONTEND_PORT="$2"; shift 2 ;;
    --no-reload)
      RELOAD=0; shift ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "Unknown argument: $1"; usage; exit 1 ;;
  esac
done

if [[ ! -d "$ROOT/backend" || ! -d "$ROOT/frontend" ]]; then
  echo "Repo not found at: $ROOT"
  exit 1
fi

DEBUG="false"
JUDGE_ENABLED="true"
ENABLE_27B_REASONING="true"
MAX_JUDGMENT_CYCLES=1

case "$MODE" in
  mock)
    DEBUG="true"
    JUDGE_ENABLED="false"
    ENABLE_27B_REASONING="false"
    MAX_JUDGMENT_CYCLES=0
    ;;
  real)
    DEBUG="false"
    ;;
  fast)
    DEBUG="false"
    JUDGE_ENABLED="false"
    ENABLE_27B_REASONING="true"
    MAX_JUDGMENT_CYCLES=0
    ;;
  fastest)
    DEBUG="false"
    JUDGE_ENABLED="false"
    ENABLE_27B_REASONING="false"
    MAX_JUDGMENT_CYCLES=0
    ;;
  *)
    echo "Unknown mode: $MODE"
    usage
    exit 1
    ;;
esac

LOG_DIR="$ROOT/medai-logs"
PID_FILE="$ROOT/.medai_pids"
mkdir -p "$LOG_DIR"

# Kill existing processes on the ports
echo "Checking for existing processes..."
lsof -ti tcp:$BACKEND_PORT | xargs -r kill -9 2>/dev/null && echo "Killed process on port $BACKEND_PORT" || true
lsof -ti tcp:$FRONTEND_PORT | xargs -r kill -9 2>/dev/null && echo "Killed process on port $FRONTEND_PORT" || true

# Wait for ports to actually clear
for i in 1 2 3 4 5; do
  if ss -tlnp 2>/dev/null | grep -qE ":($BACKEND_PORT|$FRONTEND_PORT) "; then
    echo "Waiting for ports to clear... ($i)"
    sleep 1
  else
    break
  fi
done

# Clear old logs
> "$LOG_DIR/backend.log"
> "$LOG_DIR/frontend.log"

PYTHON="$ROOT/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="python"
fi

BACKEND_CMD=("$PYTHON" -m uvicorn medai.main:app --host 0.0.0.0 --port "$BACKEND_PORT")
if [[ "$RELOAD" -eq 1 ]]; then
  BACKEND_CMD+=(--reload)
fi

export NVM_DIR="$HOME/.nvm"
if [[ -s "$NVM_DIR/nvm.sh" ]]; then
  # shellcheck disable=SC1090
  . "$NVM_DIR/nvm.sh"
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "npm not found. Install Node.js or run: source $NVM_DIR/nvm.sh"
  exit 1
fi

echo "Starting backend (mode=$MODE) on :$BACKEND_PORT"
(
  cd "$ROOT/backend"
  DEBUG="$DEBUG" \
  JUDGE_ENABLED="$JUDGE_ENABLED" \
  ENABLE_27B_REASONING="$ENABLE_27B_REASONING" \
  MAX_JUDGMENT_CYCLES="$MAX_JUDGMENT_CYCLES" \
  "${BACKEND_CMD[@]}"
) > "$LOG_DIR/backend.log" 2>&1 &
BACKEND_PID=$!

sleep 1

echo "Starting frontend on :$FRONTEND_PORT"
(
  cd "$ROOT/frontend"
  npm run dev -- -p "$FRONTEND_PORT"
) > "$LOG_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!

cat > "$PID_FILE" <<EOF
BACKEND_PID=$BACKEND_PID
FRONTEND_PID=$FRONTEND_PID
EOF

echo "Backend PID: $BACKEND_PID (log: $LOG_DIR/backend.log)"
echo "Frontend PID: $FRONTEND_PID (log: $LOG_DIR/frontend.log)"
echo "Open: http://localhost:$FRONTEND_PORT"
