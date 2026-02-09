# MedAI — Agentic Medical AI Assistant

> End-to-end medical AI platform using Claude orchestration, MedGemma specialist models, and explainable AI reports.

Built for the **AgentForge Hackathon** by SoftServe.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Frontend (Next.js 14)          :3000                       │
│  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐     │
│  │ Auth    │ │ Agent    │ │ Patient  │ │ Citations  │     │
│  │ Login/  │ │ Chat +   │ │ Timeline │ │ Sidebar    │     │
│  │Register │ │ Pipeline │ │          │ │            │     │
│  └─────────┘ └──────────┘ └──────────┘ └────────────┘     │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP + SSE
┌──────────────────────────▼──────────────────────────────────┐
│  Backend (FastAPI)              :8000                        │
│  ┌──────────────────────────────────────────────────┐       │
│  │ Claude Orchestrator (Sonnet 4)                   │       │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────────┐     │       │
│  │  │ ROUTE    │→│ DISPATCH │→│ COLLECT      │     │       │
│  │  │ (decide  │ │ (parallel│ │ (results)    │     │       │
│  │  │  tools)  │ │  tools)  │ │              │     │       │
│  │  └──────────┘ └──────────┘ └──────────────┘     │       │
│  │  ┌──────────┐ ┌──────────┐                       │       │
│  │  │ JUDGE    │→│ REPORT   │                       │       │
│  │  │ (verify) │ │ (final)  │                       │       │
│  │  └──────────┘ └──────────┘                       │       │
│  └──────────────────────────────────────────────────┘       │
│                                                              │
│  Specialist Tools (HTTP → Modal GPU endpoints):              │
│  ┌────────────┐ ┌────────────┐ ┌──────────────┐            │
│  │ MedGemma   │ │ MedGemma   │ │ MedSigLIP    │            │
│  │ 4B (image) │ │ 27B (text) │ │ (heatmaps)   │            │
│  └────────────┘ └────────────┘ └──────────────┘            │
│  ┌────────────┐ ┌────────────┐                              │
│  │ HeAR       │ │  Whisper   │                              │
│  │ (audio)    │ │  (speech)  │                              │
│  └────────────┘ └────────────┘                              │
└─────────────────────────────────────────────────────────────┘
                    │
              Modal (cloud GPU)
```

### Pipeline Flow

1. **ROUTE** — Claude analyzes the case and decides which specialist tools to invoke
2. **DISPATCH** — Selected tools run in parallel via HTTP to Modal GPU endpoints
3. **COLLECT** — Results gathered; if Claude didn't call MedSigLIP for images, it's auto-dispatched
4. **JUDGE** — A separate Claude agent evaluates consensus across tool outputs
5. **REPORT** — Final structured report with findings, plan, and explainability artifacts

### Real-time Progress (SSE)

The frontend uses Server-Sent Events to stream pipeline progress to the UI in real-time. Each tool start/complete/error event is displayed as the analysis runs, giving doctors visibility into what's happening during the 30-90 second analysis.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js 14 (App Router), React 18, TypeScript, Tailwind CSS, Zustand, TanStack Query |
| **Backend** | FastAPI, Python 3.11+, Pydantic v2, structlog, SQLAlchemy (async) |
| **AI Orchestrator** | Claude Sonnet 4 (Anthropic) — tool-use API with parallel calls |
| **Image Analysis** | MedGemma 4B IT (Google) — multimodal medical image understanding |
| **Text Reasoning** | MedGemma 27B IT (Google) — clinical text reasoning |
| **Explainability** | MedSigLIP (Google) — zero-shot medical image heatmaps |
| **Audio Analysis** | HeAR (Google) — health acoustic recognition |
| **Speech-to-Text** | MedASR — medical speech recognition |
| **GPU Inference** | Modal (serverless GPU, T4/A10G) |
| **Database** | SQLite (dev) / PostgreSQL (prod) |
| **Auth** | JWT (python-jose + bcrypt) |

---

## Prerequisites

- **Python 3.11+** with `pip`
- **Node.js 18+** with `npm`
- **Anthropic API key** (for Claude orchestrator)
- **Modal account** (for GPU inference — optional for mock mode)

---

## Quick Start

### 1. Clone

```bash
git clone <repo-url>
cd Agentic-MedAI-SoftServe
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv ../.venv
source ../.venv/bin/activate

# Install all dependencies
pip install -e ".[dev,db,ml]"

# Configure environment
cp .env.example .env
# Edit .env — set ANTHROPIC_API_KEY at minimum

# Initialize database (auto-creates medai.db)
# Database is auto-initialized on startup, or run migrations:
# alembic upgrade head

cd ..
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install
# This creates node_modules/ (~300MB) — this is normal for Node.js projects.
# node_modules/ is in .gitignore and NEVER committed to git.
# Only package.json and package-lock.json are tracked.

# Environment (usually no changes needed)
cp .env.example .env.local

cd ..
```

### 4. Run

Use the convenience scripts:

```bash
# Mock mode (no GPU needed, instant responses)
./medai-run.sh --mode mock

# Real mode (calls Modal GPU endpoints + Claude)
./medai-run.sh --mode real

# Fast mode (no judge, with 27B reasoning)
./medai-run.sh --mode fast

# Check status
./medai-status.sh

# Stop everything
./medai-stop.sh
```

Or run manually:

```bash
# Terminal 1: Backend
cd backend
source ../.venv/bin/activate
uvicorn medai.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev
```

Open **http://localhost:3000** in your browser.

### 5. Default Login

| Email | Password | Role |
|-------|----------|------|
| `admin@medai.com` | `admin123` | admin |
| `doctor@medai.com` | `doctor123` | doctor |

---

## Project Structure

```
Agentic-MedAI-SoftServe/
├── backend/                 # FastAPI backend
│   ├── src/medai/
│   │   ├── main.py          # App factory, route registration
│   │   ├── config.py        # Settings (from .env)
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── auth.py       # Login/register/logout
│   │   │   │   ├── cases.py      # Case analysis + SSE stream
│   │   │   │   ├── files.py      # File upload (images/audio/docs)
│   │   │   │   ├── patients.py   # Patient CRUD + timeline
│   │   │   │   ├── health.py     # Health check
│   │   │   │   └── transcription.py
│   │   │   ├── auth.py           # JWT middleware
│   │   │   └── dependencies.py   # DI container
│   │   ├── services/
│   │   │   ├── orchestrator.py   # Claude orchestrator (brain)
│   │   │   ├── judge.py          # Judge agent (consensus)
│   │   │   ├── pipeline_events.py # SSE event bus
│   │   │   ├── tool_registry.py  # Tool registration
│   │   │   └── artifact_storage.py
│   │   ├── tools/
│   │   │   └── http.py           # Modal endpoint callers
│   │   ├── domain/
│   │   │   ├── entities.py       # Core data models
│   │   │   ├── schemas.py        # API request/response shapes
│   │   │   └── interfaces.py     # Abstract base classes
│   │   └── repositories/
│   │       ├── database.py       # SQLAlchemy setup
│   │       └── *.py              # Data access layer
│   ├── tests/
│   ├── alembic/                  # DB migrations
│   ├── storage/                  # Local artifact storage
│   ├── pyproject.toml            # Python dependencies
│   └── .env                      # Environment config
│
├── frontend/                # Next.js frontend
│   ├── src/
│   │   ├── app/
│   │   │   ├── agent/page.tsx    # Main chat + analysis UI
│   │   │   ├── case/[id]/        # Report details
│   │   │   └── login/page.tsx    # Auth pages
│   │   ├── components/
│   │   │   ├── agent/            # Chat, input, citations
│   │   │   └── shared/           # Status indicator, toast
│   │   ├── lib/
│   │   │   ├── api/client.ts     # HTTP + SSE client
│   │   │   ├── api/types.ts      # API type definitions
│   │   │   ├── store.ts          # Zustand state
│   │   │   └── types.ts          # Frontend types
│   │   └── providers/
│   │       └── AuthProvider.tsx   # Auth context
│   ├── package.json              # Node.js dependencies
│   └── .env.local                # Frontend env config
│
├── deploy/                  # Modal GPU deployment scripts
│   └── modal/
│       ├── medgemma_4b.py        # MedGemma 4B endpoint
│       ├── medgemma_27b.py       # MedGemma 27B endpoint
│       ├── siglip_explainability.py # MedSigLIP endpoint
│       ├── hear_audio.py         # HeAR audio endpoint
│       └── deploy_all.sh         # Deploy all to Modal
│
├── test_samples/            # Sample test files
│   ├── sample_medical_report.pdf
│   └── sample_pneumonia_cough.wav
│
├── medai-run.sh             # Start backend + frontend
├── medai-stop.sh            # Stop all services
├── medai-status.sh          # Check service status
├── docker-compose.yml       # Docker deployment
├── DEPLOY.md                # Cloud deployment guide
└── README.md                # This file
```

---

## Run Modes

| Mode | `DEBUG` | Judge | 27B | Use Case |
|------|---------|-------|-----|----------|
| `mock` | `true` | off | off | Development — instant mock responses, no API keys needed |
| `real` | `false` | on | on | Full pipeline — all models, full validation |
| `fast` | `false` | off | on | Demo — real analysis without judge overhead |
| `fastest` | `false` | off | off | Quick demo — image + history only |

```bash
./medai-run.sh --mode mock
./medai-run.sh --mode real
./medai-run.sh --mode fast
./medai-run.sh --mode fastest --backend-port 8001 --frontend-port 3001
./medai-stop.sh
```

---

## Environment Variables

All backend config is in `backend/.env`. Key variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Claude API key for orchestrator + judge |
| `ORCHESTRATOR_MODEL` | No | Claude model (default: `claude-sonnet-4-5-20250929`) |
| `ORCHESTRATOR_MAX_TOKENS` | No | Max tokens for tool-use loop (default: 8192) |
| `JUDGE_MAX_TOKENS` | No | Max tokens for judge verdict (default: 4096) |
| `JUDGE_ENABLED` | No | Enable judge validation (default: true) |
| `ENABLE_27B_REASONING` | No | Enable MedGemma 27B (default: true) |
| `DEBUG` | No | Mock mode when true (default: false) |
| `MEDGEMMA_4B_ENDPOINT` | No* | Modal endpoint for MedGemma 4B |
| `MEDGEMMA_27B_ENDPOINT` | No* | Modal endpoint for MedGemma 27B |
| `MEDSIGLIP_ENDPOINT` | No* | Modal endpoint for MedSigLIP |
| `HEAR_ENDPOINT` | No* | Modal endpoint for HeAR |
| `DATABASE_URL` | No | SQLite (default) or PostgreSQL URL |
| `JWT_SECRET` | No | Secret for JWT tokens (auto-generated if missing) |

*Required when `DEBUG=false` (real mode).

Frontend config is in `frontend/.env.local`:

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Backend base URL (default: `http://localhost:8000`) |

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/api/v1/auth/register` | Register new user |
| `POST` | `/api/v1/auth/login` | Login, get JWT token |
| `GET` | `/api/v1/auth/me` | Current user info |
| `POST` | `/api/v1/auth/logout` | Logout |
| `POST` | `/api/v1/cases/analyze` | Submit case for AI analysis |
| `POST` | `/api/v1/cases/analyze/stream` | SSE streaming analysis with progress |
| `GET` | `/api/v1/cases/reports/{id}` | Get report by ID |
| `POST` | `/api/v1/cases/approve` | Approve/reject report |
| `POST` | `/api/v1/files/upload` | Upload files (multipart) |
| `GET` | `/api/v1/patients` | List patients |
| `POST` | `/api/v1/patients` | Create patient |
| `GET` | `/api/v1/patients/{id}/timeline` | Patient timeline |
| `POST` | `/api/v1/transcription/transcribe` | Audio transcription |

Interactive API docs: **http://localhost:8000/docs**

---

## Deploying GPU Models to Modal

```bash
cd deploy/modal

# Deploy all models at once
bash deploy_all.sh

# Or deploy individually
modal deploy medgemma_4b.py
modal deploy medgemma_27b.py
modal deploy siglip_explainability.py
modal deploy hear_audio.py
```

After deployment, update the endpoint URLs in `backend/.env`.

---

## Testing

```bash
# Backend unit tests
cd backend
source ../.venv/bin/activate
pytest tests/unit/ -v

# Backend integration tests (requires running server)
pytest tests/integration/ -v

# End-to-end test (requires running server + Modal endpoints)
pytest tests/e2e_live_test.py -v

# Frontend tests
cd frontend
npm test
```

---

## Docker Deployment

```bash
# Copy and configure environment
cp .env.docker.example .env
# Edit .env: set ANTHROPIC_API_KEY, JWT_SECRET

# Start all services
docker-compose up --build

# Services:
#   Frontend:  http://localhost:3000
#   Backend:   http://localhost:8000
#   PostgreSQL: localhost:5432
```

See [DEPLOY.md](DEPLOY.md) for cloud deployment (GCP Cloud Run + Cloud SQL).

---

## About `node_modules/`

If you're new to Node.js: the `frontend/node_modules/` directory contains all installed JavaScript packages. It's typically 200-400 MB and contains thousands of files — this is **completely normal** for Node.js projects.

- `node_modules/` is **never committed to git** (it's in `.gitignore`)
- Only `package.json` (dependency declarations) and `package-lock.json` (exact versions) are tracked
- Running `npm install` in `frontend/` recreates `node_modules/` from these lock files
- This is analogous to Python's `pip install` + virtual environments

---

## License

MIT — see [LICENSE](LICENSE)
fastest: DEBUG=false, judge off, 27B off
