<div align="center">

# MedAI — Agentic Medical AI Assistant

**End-to-end medical AI platform with Claude orchestration, MedGemma specialist models, and explainable AI reports.**

Built for the **AgentForge Hackathon** by **SoftServe**

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![Next.js 14](https://img.shields.io/badge/Next.js-14-000000?logo=next.js&logoColor=white)](https://nextjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Claude Sonnet 4](https://img.shields.io/badge/Claude-Sonnet_4-D97706?logo=anthropic&logoColor=white)](https://anthropic.com)
[![Modal](https://img.shields.io/badge/Modal-GPU_Inference-4F46E5)](https://modal.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

---

## Table of Contents

- [MedAI — Agentic Medical AI Assistant](#medai--agentic-medical-ai-assistant)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [Architecture](#architecture)
    - [Core Agent Pipeline](#core-agent-pipeline)
    - [Domain Entities](#domain-entities)
    - [Real-time Progress (SSE)](#real-time-progress-sse)
  - [Tech Stack](#tech-stack)
  - [Quick Start](#quick-start)
    - [Prerequisites](#prerequisites)
    - [1. Clone](#1-clone)
    - [2. Backend](#2-backend)
    - [3. Frontend](#3-frontend)
    - [4. Run](#4-run)
    - [5. Default Credentials](#5-default-credentials)
  - [Run Modes](#run-modes)
  - [Project Structure](#project-structure)
  - [Environment Variables](#environment-variables)
    - [Backend (`backend/.env`)](#backend-backendenv)
    - [Frontend (`frontend/.env.local`)](#frontend-frontendenvlocal)
  - [API Reference](#api-reference)
  - [GPU Model Deployment](#gpu-model-deployment)
  - [Testing](#testing)
  - [Docker Deployment](#docker-deployment)
  - [License](#license)

---

## Overview

MedAI is a **multi-agent medical AI assistant** that combines a Claude Sonnet 4 orchestrator with specialized Google medical models (MedGemma, MedSigLIP, HeAR) to analyze medical images, audio, and clinical text. The platform produces **explainable, structured reports** with heatmap visualizations and a built-in judge for cross-modal consensus validation.

**Key capabilities:**
- **Medical image analysis** — X-rays, CT, MRI, dermatology, fundus, histopathology via MedGemma 4B
- **Clinical reasoning** — Chain-of-thought assessment with evidence citations via MedGemma 27B
- **Explainability heatmaps** — Zero-shot spatial attention maps via MedSigLIP
- **Audio analysis** — Respiratory sound classification (wheeze, crackle) via HeAR
- **Judge agent** — Cross-modal consistency verification before report finalization
- **Patient timeline** — Longitudinal tracking with historical context via RAG

---

## Architecture

### Core Agent Pipeline

The orchestrator follows a 5-phase agentic loop: **Route → Dispatch → Collect → Judge → Report**.

<p align="center">
  <img src="images_readme/core-agents-pipeline-2026-02-09-044935.png" alt="Core Agent Pipeline — Route, Dispatch, Collect, Judge, Report" width="100%" />
</p>

| Phase | Description |
|-------|-------------|
| **1. Route** | Claude analyzes the case and decides which specialist tools to invoke |
| **2. Dispatch** | Selected tools run **in parallel** via HTTP to Modal GPU endpoints |
| **3. Collect** | Results gathered; MedSigLIP auto-dispatched for any images |
| **4. Judge** | A separate Claude agent evaluates cross-modal consensus |
| **5. Report** | Final structured report with findings, plan, and explainability artifacts |

### Domain Entities

<p align="center">
  <img src="images_readme/entities-2026-02-09-042107.png" alt="Domain Entities — Users, Patients, Cases, Reports, Timeline" width="100%" />
</p>

### Real-time Progress (SSE)

The frontend uses **Server-Sent Events** to stream pipeline progress to the UI in real-time. Each tool start/complete/error event is displayed as the analysis runs, giving doctors visibility into what's happening during the 30–90 second analysis.

---

## Tech Stack

| Layer | Technology |
|:------|:-----------|
| **Frontend** | Next.js 14 (App Router) · React 18 · TypeScript · Tailwind CSS · Zustand · TanStack Query |
| **Backend** | FastAPI · Python 3.11+ · Pydantic v2 · structlog · SQLAlchemy (async) |
| **AI Orchestrator** | Claude Sonnet 4 (Anthropic) — tool-use API with parallel calls |
| **Image Analysis** | MedGemma 4B IT (Google) — multimodal medical image understanding |
| **Text Reasoning** | MedGemma 27B IT (Google) — clinical text reasoning |
| **Explainability** | MedSigLIP (Google) — zero-shot medical image heatmaps |
| **Audio Analysis** | HeAR (Google) — health acoustic recognition |
| **Speech-to-Text** | MedASR (Google) — medical speech recognition |
| **GPU Inference** | Modal (serverless GPU — T4 / A10G / A100) |
| **Database** | SQLite (dev) / PostgreSQL (prod) |
| **Auth** | JWT (python-jose + bcrypt) |

---

## Quick Start

### Prerequisites

- **Python 3.11+** with `pip`
- **Node.js 18+** with `npm`
- **Anthropic API key** (for Claude orchestrator)
- **Modal account** (for GPU inference — optional in mock mode)

### 1. Clone

```bash
git clone https://github.com/ArseniiStratiuk/Agentic-MedAI-SoftServe.git
cd Agentic-MedAI-SoftServe
```

### 2. Backend

```bash
cd backend
python3 -m venv ../.venv && source ../.venv/bin/activate
pip install -e ".[dev,db,ml]"
cp .env.example .env   # ← set ANTHROPIC_API_KEY
cd ..
```

### 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
cd ..
```

### 4. Run

```bash
# Mock mode (no GPU needed, instant responses)
./medai-run.sh --mode mock

# Real mode (all models + Claude + judge)
./medai-run.sh --mode real
```

Or manually:

```bash
# Terminal 1 — Backend
cd backend && source ../.venv/bin/activate
uvicorn medai.main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend && npm run dev
```

Open **http://localhost:3000** in your browser.

### 5. Default Credentials

| Email | Password | Role |
|:------|:---------|:-----|
| `admin@medai.com` | `admin123` | Admin |
| `doctor@medai.com` | `doctor123` | Doctor |

---

## Run Modes

| Mode | `DEBUG` | Judge | 27B | Use Case |
|:-----|:--------|:------|:----|:---------|
| **mock** | `true` | off | off | Development — instant mock responses, no API keys needed |
| **real** | `false` | on | on | Full pipeline — all models, full validation |
| **fast** | `false` | off | on | Demo — real analysis without judge overhead |
| **fastest** | `false` | off | off | Quick demo — image + history only |

```bash
./medai-run.sh --mode mock
./medai-run.sh --mode real
./medai-run.sh --mode fast
./medai-run.sh --mode fastest --backend-port 8001 --frontend-port 3001
./medai-stop.sh          # stop all services
./medai-status.sh        # check service status
```

---

## Project Structure

```
Agentic-MedAI-SoftServe/
│
├── backend/                      # FastAPI backend
│   ├── src/medai/
│   │   ├── main.py               #   App factory + route registration
│   │   ├── config.py             #   Settings (from .env)
│   │   ├── api/                  #   Routes (auth, cases, files, patients)
│   │   ├── services/             #   Orchestrator, judge, SSE, tool registry
│   │   ├── tools/                #   Modal endpoint callers
│   │   ├── domain/               #   Entities, schemas, interfaces
│   │   └── repositories/         #   SQLAlchemy data access layer
│   ├── tests/                    #   Unit, integration, e2e tests
│   ├── alembic/                  #   Database migrations
│   ├── storage/                  #   Local artifact storage
│   └── pyproject.toml            #   Python dependencies
│
├── frontend/                     # Next.js 14 frontend
│   ├── src/
│   │   ├── app/                  #   Pages (agent, case, patients, auth)
│   │   ├── components/           #   UI components (chat, citations, shared)
│   │   ├── lib/                  #   API client, Zustand store, types
│   │   └── providers/            #   Auth context
│   └── package.json              #   Node.js dependencies
│
├── deploy/                       # Deployment configs
│   └── modal/                    #   Modal GPU endpoint scripts
│       ├── medgemma_4b.py        #     Image analysis
│       ├── medgemma_27b.py       #     Text reasoning
│       ├── siglip_explainability.py  # Heatmap explainability
│       ├── hear_audio.py         #     Audio analysis
│       └── deploy_all.sh         #     Deploy all endpoints
│
├── medai-run.sh                  # Start backend + frontend
├── medai-stop.sh                 # Stop all services
├── medai-status.sh               # Check service status
├── docker-compose.yml            # Docker deployment
└── README.md
```

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Required | Default | Description |
|:---------|:---------|:--------|:------------|
| `ANTHROPIC_API_KEY` | **Yes** | — | Claude API key for orchestrator + judge |
| `ORCHESTRATOR_MODEL` | No | `claude-sonnet-4-5-20250929` | Claude model for orchestration |
| `ORCHESTRATOR_MAX_TOKENS` | No | `8192` | Max tokens for tool-use loop |
| `JUDGE_MAX_TOKENS` | No | `4096` | Max tokens for judge verdict |
| `JUDGE_ENABLED` | No | `true` | Enable judge validation |
| `ENABLE_27B_REASONING` | No | `true` | Enable MedGemma 27B |
| `DEBUG` | No | `false` | Mock mode (no external calls) |
| `MEDGEMMA_4B_ENDPOINT` | Real mode | — | Modal endpoint URL |
| `MEDGEMMA_27B_ENDPOINT` | Real mode | — | Modal endpoint URL |
| `MEDSIGLIP_ENDPOINT` | Real mode | — | Modal endpoint URL |
| `HEAR_ENDPOINT` | Real mode | — | Modal endpoint URL |
| `DATABASE_URL` | No | `sqlite:///medai.db` | SQLite or PostgreSQL URL |
| `JWT_SECRET` | No | auto-generated | JWT signing secret |

### Frontend (`frontend/.env.local`)

| Variable | Default | Description |
|:---------|:--------|:------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend base URL |

---

## API Reference

| Method | Path | Description |
|:-------|:-----|:------------|
| `GET` | `/health` | Health check |
| `POST` | `/api/v1/auth/register` | Register new user |
| `POST` | `/api/v1/auth/login` | Login → JWT token |
| `GET` | `/api/v1/auth/me` | Current user info |
| `POST` | `/api/v1/auth/logout` | Logout |
| `POST` | `/api/v1/cases/analyze` | Submit case for AI analysis |
| `POST` | `/api/v1/cases/analyze/stream` | SSE streaming analysis with progress |
| `GET` | `/api/v1/cases/reports/{id}` | Get report by ID |
| `POST` | `/api/v1/cases/approve` | Approve / reject report |
| `POST` | `/api/v1/files/upload` | Upload files (multipart) |
| `GET` | `/api/v1/patients` | List patients |
| `POST` | `/api/v1/patients` | Create patient |
| `GET` | `/api/v1/patients/{id}/timeline` | Patient timeline |
| `POST` | `/api/v1/transcription/transcribe` | Audio transcription |

> Interactive docs: **http://localhost:8000/docs**

---

## GPU Model Deployment

Deploy the specialist models to [Modal](https://modal.com) for serverless GPU inference:

```bash
cd deploy/modal

# Deploy all models at once
bash deploy_all.sh

# Or deploy individually
modal deploy medgemma_4b.py          # A10G GPU
modal deploy medgemma_27b.py         # A100-80GB GPU
modal deploy siglip_explainability.py # T4 GPU
modal deploy hear_audio.py           # T4 GPU
```

After deployment, copy the endpoint URLs into `backend/.env`.

---

## Testing

```bash
# Backend unit tests
cd backend && source ../.venv/bin/activate
pytest tests/unit/ -v

# Integration tests (requires running server)
pytest tests/integration/ -v

# End-to-end (requires server + Modal endpoints)
pytest tests/e2e_live_test.py -v

# Frontend tests
cd frontend && npm test
```

---

## Docker Deployment

```bash
cp .env.docker.example .env
# Edit .env — set ANTHROPIC_API_KEY, JWT_SECRET

docker-compose up --build
```

| Service | URL |
|:--------|:----|
| Frontend | http://localhost:3000 |
| Backend | http://localhost:8000 |
| PostgreSQL | localhost:5432 |

See [DEPLOY.md](DEPLOY.md) for cloud deployment (GCP Cloud Run + Cloud SQL).

---

## License

MIT — see [LICENSE](LICENSE)
