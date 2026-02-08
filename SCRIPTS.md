# MedAI Management Scripts

Quick-start scripts to run the full MedAI stack locally.

## Scripts

### 🚀 `./medai-run.sh` - Start Services

Starts both backend and frontend with automatic port cleanup.

**Modes:**
- `mock` (default) - Mock tools, judge OFF, 27B reasoning OFF
- `real` - Real tools, judge ON, 27B reasoning ON  
- `fast` - Real tools, judge OFF, 27B reasoning ON
- `fastest` - Real tools, judge OFF, 27B reasoning OFF

**Examples:**
```bash
# Start in mock mode (fastest, no external APIs)
./medai-run.sh

# Start with real tools and all features
./medai-run.sh --mode real

# Custom ports
./medai-run.sh --mode fast --backend-port 8001 --frontend-port 3001
```

**What it does:**
1. Kills any existing processes on ports 8000 and 3000
2. Clears old logs
3. Starts backend (uvicorn) on port 8000
4. Starts frontend (Next.js) on port 3000
5. Saves PIDs to `.medai_pids`
6. Logs to `medai-logs/backend.log` and `medai-logs/frontend.log`

### 🛑 `./medai-stop.sh` - Stop Services

Gracefully stops both services and cleans up.

```bash
./medai-stop.sh
```

**What it does:**
1. Reads PIDs from `.medai_pids`
2. Kills both processes
3. Fallback: kills any process on ports 8000/3000
4. Removes PID file

### 📊 `./medai-status.sh` - Check Status

Shows current status of all services.

```bash
./medai-status.sh
```

**Output:**
```
=== MedAI Services Status ===

✓ Backend: RUNNING (PID 40713, port 8000)
  URL: http://localhost:8000
  Docs: http://localhost:8000/docs

✓ Frontend: RUNNING (PID 38831, port 3000)
  URL: http://localhost:3000

📋 Backend log: 21 lines (medai-logs/backend.log)
📋 Frontend log: 23 lines (medai-logs/frontend.log)
```

## Quick Start

```bash
# 1. Start everything (mock mode for development)
./medai-run.sh

# 2. Check status
./medai-status.sh

# 3. Open in browser
open http://localhost:3000

# 4. View API docs
open http://localhost:8000/docs

# 5. Stop everything
./medai-stop.sh
```

## Logs

All logs are saved to `medai-logs/`:
- `backend.log` - Uvicorn/FastAPI logs
- `frontend.log` - Next.js dev server logs

View logs in real-time:
```bash
# Backend
tail -f medai-logs/backend.log

# Frontend  
tail -f medai-logs/frontend.log
```

## Troubleshooting

**Port already in use:**
```bash
./medai-stop.sh  # Force cleanup
./medai-run.sh   # Restart
```

**Check what's running:**
```bash
./medai-status.sh
```

**Manual port cleanup:**
```bash
lsof -ti tcp:8000 | xargs -r kill -9
lsof -ti tcp:3000 | xargs -r kill -9
```
