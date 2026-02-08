# Three-Way Parallel Handoff

Backend is fully validated (122 tests, E2E with RAG in 251.7s, all fields flowing). The codebase splits cleanly into three zero-conflict workstreams: **Frontend** (consumes API contracts), **GCP/Infra** (Docker + Postgres + Auth + User model), and **Arsenii** (SigLIP on Modal). No merge conflicts possible — each touches different files.

---

## Steps

### 1. Frontend Dev

Work exclusively in `frontend/src/`, consume the 3 endpoints in `backend/src/medai/api/routes/cases.py`:

- `POST /cases/analyze`
- `GET /cases/{id}/report`
- `POST /cases/approve`

Response contracts are finalized in `backend/src/medai/domain/schemas.py` — `CaseAnalysisResponse` includes `confidence_method`, `pipeline_metrics`, `specialist_summaries`, and `judgment`. Run backend locally with `DEBUG=true` (mock tools, no GPU needed).

### 2. GCP/Infra Dev — Database Layer

Create `User` entity (not yet in `backend/src/medai/domain/entities.py`), add `BaseUserRepository` ABC to `backend/src/medai/domain/interfaces.py`, implement all 4 repos (Patient, Timeline, Report, User) as SQLAlchemy async models replacing the in-memory ones in `backend/src/medai/repositories/memory.py`. The `[db]` deps (`sqlalchemy[asyncio]`, `alembic`, `asyncpg`) are already declared in `backend/pyproject.toml`. Swap them in `backend/src/medai/api/dependencies.py` where the `# TODO: Swap for SQLAlchemy repo when DB is ready` comment lives.

### 3. GCP/Infra Dev — Auth & Config

Create `Dockerfile` + `docker-compose.yml` at project root (neither exists yet), add JWT/session auth middleware to `backend/src/medai/api/main.py`, restrict CORS from `"*"` to actual frontend origin, add auth config fields (`JWT_SECRET`, `ALLOWED_ORIGINS`) to `backend/src/medai/config.py`, and create their own `.env` with `DATABASE_URL=postgresql+asyncpg://...` (the commented-out line in `backend/.env.example` shows the format). Modal endpoint URLs stay unchanged — GPU inference is **not** moved to GCP.

### 4. GCP/Infra Dev — Migrations & Deploy

Set up Alembic migrations (`alembic init`, create revisions for Patient/Timeline/FinalReport/User tables), migrate seed data from `backend/src/medai/repositories/seed.py` (3 patients, 23 events) into a data migration or fixture script, and deploy to Cloud Run + Cloud SQL.

### 5. Arsenii — SigLIP Integration

Add SigLIP Modal deploy script in `deploy/modal/` (like existing `deploy/modal/medgemma_4b.py`), create `HttpSigLipTool` in `backend/src/medai/tools/http.py` implementing `BaseTool`, register it in `backend/src/medai/api/dependencies.py`, and wire `MEDSIGLIP_ENDPOINT` (already in `backend/src/medai/config.py` defaulting to `localhost:8012`).

---

## Further Considerations

1. **`.env` max_tokens mismatch** — `.env.example` has `ORCHESTRATOR_MAX_TOKENS=4096` but code default is `16384`; the `.env` value wins via pydantic-settings. Should the GCP dev's `.env` use `16384`?
2. **Auth scope** — should auth protect all 3 endpoints or just `approve`? Recommend: all 3 (JWT bearer), with an optional `X-API-Key` bypass for E2E tests.
3. **Seed data strategy** — Alembic data migration vs. a management command (`python -m medai seed`)? Recommend: management command, so it's idempotent and rerunnable in dev.
