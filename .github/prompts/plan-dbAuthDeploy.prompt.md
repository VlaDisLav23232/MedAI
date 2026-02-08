# Database + Auth + Docker + Deploy (Tasks 2–4)

Replace in-memory repositories with async SQLAlchemy backed by PostgreSQL, add JWT auth matching the existing frontend contract, containerize with Docker Compose, set up Alembic migrations + seed command, and provide GCP Cloud Run + Cloud SQL deployment instructions. Three sequential tasks — DB layer first, then auth on top, then infra/deploy.

---

## Task 2 — Database Layer

### 2.1 Add `User` entity to `backend/src/medai/domain/entities.py`

- Fields: `id` (string, `USR-{uuid4().hex[:8]}`), `email` (str, unique), `hashed_password` (str), `name` (str), `role` (str, one of `doctor | admin | nurse`), `created_at` (datetime), `is_active` (bool, default True)
- Add `UserRole` enum: `DOCTOR`, `ADMIN`, `NURSE`

### 2.2 Add `BaseUserRepository` ABC to `backend/src/medai/domain/interfaces.py`

- Methods: `get_by_id(user_id: str) -> User | None`, `get_by_email(email: str) -> User | None`, `create(user: User) -> User`, `list_all() -> list[User]`

### 2.3 Add auth schemas to `backend/src/medai/domain/schemas.py`

- `LoginRequest(email: str, password: str)`
- `RegisterRequest(email: str, password: str, name: str, role: str = "doctor")`
- `AuthResponse(access_token: str, token_type: str = "bearer", user: UserResponse)`
- `UserResponse(id: str, email: str, name: str, role: str)`

### 2.4 Create SQLAlchemy table models — `backend/src/medai/repositories/models.py`

- Shared `Base = declarative_base()` with `AsyncAttrs` mixin
- Tables: `users`, `patients`, `timeline_events`, `final_reports`
- Map Pydantic entity fields → SA `Column` definitions (all IDs are `String(20)` PKs, not auto-increment)
- `timeline_events.metadata_` column as `JSON` type (rename to avoid Python reserved word)
- `final_reports` stores nested Pydantic objects (`findings`, `reasoning_trace`, `specialist_outputs`, `judge_verdict`, `pipeline_metrics`) as `JSON` columns
- Add `created_at` default at DB level via `server_default=func.now()`

### 2.5 Create async session factory — `backend/src/medai/repositories/database.py`

- `create_async_engine(settings.database_url)` with `echo=settings.debug`
- `async_sessionmaker` bound to engine
- `async def get_db_session()` — FastAPI dependency yielding `AsyncSession`
- `async def init_db(engine)` — creates all tables (for dev; Alembic for prod)
- `async def dispose_db(engine)` — clean shutdown

### 2.6 Create SQLAlchemy repository implementations — `backend/src/medai/repositories/sqlalchemy.py`

- `SqlAlchemyPatientRepository(session: AsyncSession)` implementing `BasePatientRepository`
- `SqlAlchemyTimelineRepository(session: AsyncSession)` implementing `BaseTimelineRepository`
- `SqlAlchemyReportRepository(session: AsyncSession)` implementing `BaseReportRepository`
- `SqlAlchemyUserRepository(session: AsyncSession)` implementing `BaseUserRepository`
- Each repo converts between Pydantic domain entities ↔ SA row models via `_to_entity()` / `_to_row()` helper methods
- `get_for_patient` sorts by date DESC (matches InMemory behavior)
- `update_approval` uses `session.execute(update(...).where(...))`

### 2.7 Update `backend/src/medai/api/dependencies.py`

- Replace `InMemory*` imports with `SqlAlchemy*` imports
- Add `get_db_session` as a FastAPI dependency (yields from sessionmaker)
- Change `get_patient_repository`, `get_timeline_repository`, `get_report_repository` to accept `session: AsyncSession = Depends(get_db_session)` and return SA repos
- Remove `@lru_cache` from repo factories (session is per-request, not singleton)
- Keep `@lru_cache` on engine/sessionmaker creation (these ARE singletons)

### 2.8 Update `backend/src/medai/main.py` lifespan

- Import `create_async_engine`, `dispose_db` from `repositories.database`
- In lifespan startup: create engine, run `init_db` if debug mode
- In lifespan shutdown: call `dispose_db`
- Store engine on `app.state.engine`

---

## Task 3 — Auth & Config

### 3.1 Add JWT deps to `backend/pyproject.toml` core dependencies

- `python-jose[cryptography]>=3.3.0`
- `passlib[bcrypt]>=1.7.4`

### 3.2 Add config fields to `backend/src/medai/config.py`

- `jwt_secret: str = Field(default="CHANGE-ME-IN-PRODUCTION")`
- `jwt_algorithm: str = Field(default="HS256")`
- `access_token_expire_minutes: int = Field(default=60)`
- `allowed_origins: list[str] = Field(default=["http://localhost:3000"])`

### 3.3 Create auth utilities — `backend/src/medai/api/auth.py`

- `hash_password(plain: str) -> str` — `passlib.context.CryptContext(schemes=["bcrypt"])`
- `verify_password(plain: str, hashed: str) -> bool`
- `create_access_token(data: dict, expires_delta: timedelta | None) -> str` — `jose.jwt.encode`
- `get_current_user(token: str = Depends(OAuth2PasswordBearer), session = Depends(get_db_session)) -> User` — decodes JWT, fetches user from `SqlAlchemyUserRepository`, raises 401 if invalid/expired
- `require_role(*roles: str)` — dependency factory that checks `current_user.role in roles`

### 3.4 Create auth routes — `backend/src/medai/api/routes/auth.py`

- `POST /auth/login` — validates email+password via `verify_password`, returns `AuthResponse`
- `POST /auth/register` — hashes password, creates user via `UserRepository.create`, returns `AuthResponse`
- `GET /auth/me` — `Depends(get_current_user)`, returns `UserResponse`
- Error responses: `HTTPException(401, detail="Invalid credentials")`, `HTTPException(409, detail="Email already registered")`

### 3.5 Register auth router + restrict CORS in `backend/src/medai/main.py`

- `app.include_router(auth.router, prefix="/api/v1")`
- Update CORS: use `settings.allowed_origins` instead of `["*"]`

### 3.6 Add auth guards to existing routes

- `patients.py`: add `current_user: User = Depends(get_current_user)` to all endpoints
- `cases.py`: add `current_user: User = Depends(get_current_user)` to all endpoints
- `health.py`: NO auth (stays public for load balancers / k8s probes)

### 3.7 Create `backend/Dockerfile`

- Multi-stage: `python:3.11-slim` base
- Stage 1 (builder): install build deps, `pip install .[db]`
- Stage 2 (runtime): copy venv, copy source, expose 8000
- `CMD ["uvicorn", "medai.main:app", "--host", "0.0.0.0", "--port", "8000"]`
- Non-root user for security

### 3.8 Create `docker-compose.yml` at project root

- `db` service: `postgres:16-alpine`, port 5432, volume for persistence, healthcheck
- `backend` service: builds `./backend`, depends on `db`, env vars for `DATABASE_URL=postgresql+asyncpg://medai:medai@db:5432/medai`, `ANTHROPIC_API_KEY`, `JWT_SECRET`, ports 8000
- `frontend` service: builds `./frontend`, depends on `backend`, env `NEXT_PUBLIC_API_URL=http://backend:8000`, ports 3000
- Shared `.env` file for secrets

### 3.9 Update `backend/.env.example`

- Add `JWT_SECRET=`, `ALLOWED_ORIGINS=http://localhost:3000`, `ACCESS_TOKEN_EXPIRE_MINUTES=60`

---

## Task 4 — Migrations & Deploy

### 4.1 Initialize Alembic in `backend/`

- `alembic.ini` at `backend/alembic.ini`
- `alembic/env.py` configured for async with `run_async_migrations`
- Target metadata = `Base.metadata` from `repositories/models.py`
- `sqlalchemy.url` reads from `DATABASE_URL` env var (overrides `alembic.ini` placeholder)

### 4.2 Create initial migration

- Auto-generate revision: `users`, `patients`, `timeline_events`, `final_reports` tables
- All indexes: unique on `users.email`, index on `timeline_events.patient_id`, index on `final_reports.patient_id`

### 4.3 Create seed management command — `backend/src/medai/cli/seed.py`

- Invoked as `python -m medai.cli.seed` (add `__main__.py` hook)
- Reuses `create_seed_patients()` + `create_seed_timeline_events()` from existing `seed.py`
- Creates a default admin user: `admin@medai.com` / `admin123` (configurable via env)
- Idempotent: checks if data exists before inserting (upsert by PK)
- Prints summary of seeded records

### 4.4 Add DB connectivity to `/health` endpoint in `backend/src/medai/api/routes/health.py`

- Add `db_connected: bool` field to `HealthResponse`
- Execute `SELECT 1` via session to verify connectivity
- Catch exceptions gracefully — return `db_connected: false` but don't crash

### 4.5 Add Makefile targets to `backend/Makefile`

- `make db-migrate MSG="..."` → `alembic revision --autogenerate -m "$(MSG)"`
- `make db-upgrade` → `alembic upgrade head`
- `make db-downgrade` → `alembic downgrade -1`
- `make seed` → `python -m medai.cli.seed`
- `make docker-up` → `docker-compose up --build`
- `make docker-down` → `docker-compose down`

### 4.6 Write GCP deployment guide — `DEPLOY.md` at project root

- **Prerequisites**: `gcloud` CLI installed, project created, billing enabled ($300 trial)
- **Step 1**: Enable Cloud SQL Admin API, Cloud Run API, Artifact Registry API
- **Step 2**: Create Cloud SQL PostgreSQL 15 instance (db-f1-micro, cheapest)
- **Step 3**: Create database + user via `gcloud sql`
- **Step 4**: Build & push Docker image to Artifact Registry
- **Step 5**: Deploy to Cloud Run with `--add-cloudsql-instances` flag, env vars for `DATABASE_URL`, `JWT_SECRET`, `ANTHROPIC_API_KEY`
- **Step 6**: Run migrations via Cloud Run job or one-off container
- **Step 7**: Run seed command
- **Step 8**: Update `ALLOWED_ORIGINS` to Cloud Run frontend URL
- **Cost estimate**: ~$7–15/month within free tier

---

## Verification

1. **Task 2**: `docker-compose up db`, run `make db-upgrade`, run `make seed`, then `make run` — hit `/api/v1/patients` and verify the 3 demo patients return from Postgres (not in-memory)
2. **Task 3**: `POST /api/v1/auth/register` with `{"email":"test@test.com","password":"test123","name":"Test","role":"doctor"}` → get `access_token`; use token as `Authorization: Bearer <token>` on `GET /api/v1/patients` → 200; omit token → 401; frontend login page → works end-to-end
3. **Task 4**: `docker-compose up --build` — all 3 services start, frontend at `localhost:3000` can register/login/view patients with real Postgres data. Follow `DEPLOY.md` for GCP deployment.

---

## Decisions

- **Auth on all endpoints** (except `/health`): consistent security posture
- **PostgreSQL in Docker for local dev**: no SQLite fallback — ensures parity with production
- **Seed via management command** (`python -m medai.cli.seed`): idempotent, rerunnable, not tied to migration history
- **`python-jose` for JWT**: widely used with FastAPI, `OAuth2PasswordBearer` integration out of the box
- **Multi-stage Dockerfile**: keeps image small (~150MB vs ~800MB)
- **Session-per-request DI**: repos are NOT singletons anymore — each request gets its own `AsyncSession`, committed/rolled back properly
- **JSON columns for nested Pydantic data**: `findings`, `reasoning_trace`, `specialist_outputs`, `judge_verdict`, `pipeline_metrics` stored as JSON — avoids over-normalization for a prototype
- **Frontend unchanged**: backend auth contract matches exactly what `frontend/src/lib/api/client.ts` and `frontend/src/providers/AuthProvider.tsx` already expect

---

## Frontend Auth Contract (what backend must match)

| Endpoint | Method | Body | Response |
|----------|--------|------|----------|
| `/api/v1/auth/login` | POST | `{email, password}` | `{access_token, token_type, user: {id, email, name, role}}` |
| `/api/v1/auth/register` | POST | `{email, password, name, role?}` | same |
| `/api/v1/auth/me` | GET | Bearer token | `{id, email, name, role}` |

- Roles: `"doctor" | "admin" | "nurse"`
- Token stored as `"medai-auth-token"` in localStorage
- Injected as `Authorization: Bearer <token>` header
- Error format: `{"detail": "..."}` (FastAPI convention)
