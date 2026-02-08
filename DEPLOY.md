# MedAI — Deployment Guide

## Table of Contents

1. [Local Development (Docker Compose)](#1-local-development-docker-compose)
2. [GCP Cloud Run + Cloud SQL](#2-gcp-cloud-run--cloud-sql)
3. [Environment Variables Reference](#3-environment-variables-reference)

---

## 1. Local Development (Docker Compose)

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- `ANTHROPIC_API_KEY` (get from [console.anthropic.com](https://console.anthropic.com))

### Quick Start

```bash
# 1. Clone and enter the project
cd Agentic-MedAI-SoftServe

# 2. Create .env from template
cp .env.docker.example .env
# Edit .env and set your ANTHROPIC_API_KEY and JWT_SECRET

# 3. Start all services (PostgreSQL + Backend + Frontend)
docker-compose up --build

# 4. In another terminal, run migrations and seed data
docker-compose exec backend alembic upgrade head
docker-compose exec backend python -m medai.cli.seed
```

Services will be available at:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5432

### Default Credentials (after seed)

| User | Email | Password | Role |
|------|-------|----------|------|
| Admin | admin@medai.com | admin123 | admin |
| Doctor | doctor@medai.com | doctor123 | doctor |

### Useful Commands

```bash
# View logs
docker-compose logs -f backend

# Run only PostgreSQL (for local backend dev)
docker-compose up -d db

# Stop all services
docker-compose down

# Reset database (delete volume)
docker-compose down -v
```

### Local Backend Without Docker

If you prefer running the backend directly:

```bash
# 1. Start PostgreSQL only
docker-compose up -d db

# 2. Install dependencies
cd backend
pip install -e ".[dev,db]"

# 3. Set up .env
cp .env.example .env
# Edit DATABASE_URL=postgresql+asyncpg://medai:medai@localhost:5432/medai

# 4. Run migrations + seed
alembic upgrade head
python -m medai.cli.seed

# 5. Start backend with hot reload
make run
```

---

## 2. GCP Cloud Run + Cloud SQL

### Prerequisites

- [Google Cloud account](https://cloud.google.com/) with billing enabled ($300 free trial works)
- [gcloud CLI](https://cloud.google.com/sdk/docs/install) installed and authenticated
- Docker installed locally

### Step 1: Set Up GCP Project

```bash
# Set your project ID
export GCP_PROJECT=your-project-id
export GCP_REGION=us-central1

# Authenticate
gcloud auth login
gcloud config set project $GCP_PROJECT

# Enable required APIs
gcloud services enable \
    sqladmin.googleapis.com \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com
```

### Step 2: Create Cloud SQL Instance

```bash
# Create PostgreSQL 15 instance (db-f1-micro = cheapest, ~$7/month)
gcloud sql instances create medai-db \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=$GCP_REGION \
    --storage-size=10GB \
    --storage-auto-increase

# Create database
gcloud sql databases create medai --instance=medai-db

# Set database user password
gcloud sql users set-password postgres \
    --instance=medai-db \
    --password=YOUR_SECURE_PASSWORD

# Get the connection name (you'll need this later)
gcloud sql instances describe medai-db --format="value(connectionName)"
# Output: your-project-id:us-central1:medai-db
```

### Step 3: Create Artifact Registry Repository

```bash
# Create Docker repository
gcloud artifacts repositories create medai-repo \
    --repository-format=docker \
    --location=$GCP_REGION

# Configure Docker auth
gcloud auth configure-docker $GCP_REGION-docker.pkg.dev
```

### Step 4: Build and Push Docker Image

```bash
# Build the backend image
cd backend
docker build -t $GCP_REGION-docker.pkg.dev/$GCP_PROJECT/medai-repo/medai-backend:latest .

# Push to Artifact Registry
docker push $GCP_REGION-docker.pkg.dev/$GCP_PROJECT/medai-repo/medai-backend:latest
```

### Step 5: Deploy to Cloud Run

```bash
# Get the Cloud SQL connection name
export SQL_CONNECTION=$(gcloud sql instances describe medai-db --format="value(connectionName)")

# Deploy
gcloud run deploy medai-backend \
    --image=$GCP_REGION-docker.pkg.dev/$GCP_PROJECT/medai-repo/medai-backend:latest \
    --region=$GCP_REGION \
    --platform=managed \
    --allow-unauthenticated \
    --port=8000 \
    --memory=512Mi \
    --cpu=1 \
    --min-instances=0 \
    --max-instances=3 \
    --add-cloudsql-instances=$SQL_CONNECTION \
    --set-env-vars="DATABASE_URL=postgresql+asyncpg://postgres:YOUR_SECURE_PASSWORD@/$GCP_PROJECT:$GCP_REGION:medai-db/medai?host=/cloudsql/$SQL_CONNECTION" \
    --set-env-vars="ANTHROPIC_API_KEY=sk-ant-YOUR_KEY" \
    --set-env-vars="JWT_SECRET=YOUR_JWT_SECRET" \
    --set-env-vars="ALLOWED_ORIGINS=https://your-frontend-url.com" \
    --set-env-vars="DEBUG=false"
```

> **Note**: Cloud SQL uses Unix sockets, so the DATABASE_URL format is different.
> For Cloud Run, use: `postgresql+asyncpg://user:pass@/dbname?host=/cloudsql/CONNECTION_NAME`

### Step 6: Run Migrations

```bash
# Option A: Run as a Cloud Run job
gcloud run jobs create medai-migrate \
    --image=$GCP_REGION-docker.pkg.dev/$GCP_PROJECT/medai-repo/medai-backend:latest \
    --region=$GCP_REGION \
    --add-cloudsql-instances=$SQL_CONNECTION \
    --set-env-vars="DATABASE_URL=postgresql+asyncpg://postgres:YOUR_SECURE_PASSWORD@/$GCP_PROJECT:$GCP_REGION:medai-db/medai?host=/cloudsql/$SQL_CONNECTION" \
    --command="alembic" \
    --args="upgrade,head"

gcloud run jobs execute medai-migrate --region=$GCP_REGION --wait

# Option B: Run migrations locally via Cloud SQL Proxy
# Install: https://cloud.google.com/sql/docs/postgres/sql-proxy
cloud-sql-proxy $SQL_CONNECTION &
cd backend
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_SECURE_PASSWORD@localhost:5432/medai alembic upgrade head
```

### Step 7: Seed Data

```bash
# Via Cloud Run job
gcloud run jobs create medai-seed \
    --image=$GCP_REGION-docker.pkg.dev/$GCP_PROJECT/medai-repo/medai-backend:latest \
    --region=$GCP_REGION \
    --add-cloudsql-instances=$SQL_CONNECTION \
    --set-env-vars="DATABASE_URL=postgresql+asyncpg://postgres:YOUR_SECURE_PASSWORD@/$GCP_PROJECT:$GCP_REGION:medai-db/medai?host=/cloudsql/$SQL_CONNECTION" \
    --set-env-vars="ANTHROPIC_API_KEY=dummy" \
    --command="python" \
    --args="-m,medai.cli.seed"

gcloud run jobs execute medai-seed --region=$GCP_REGION --wait
```

### Step 8: Deploy Frontend

```bash
# Build frontend image
cd frontend
docker build -t $GCP_REGION-docker.pkg.dev/$GCP_PROJECT/medai-repo/medai-frontend:latest \
    --build-arg NEXT_PUBLIC_API_URL=https://medai-backend-HASH-uc.a.run.app .

docker push $GCP_REGION-docker.pkg.dev/$GCP_PROJECT/medai-repo/medai-frontend:latest

# Deploy
gcloud run deploy medai-frontend \
    --image=$GCP_REGION-docker.pkg.dev/$GCP_PROJECT/medai-repo/medai-frontend:latest \
    --region=$GCP_REGION \
    --platform=managed \
    --allow-unauthenticated \
    --port=3000
```

### Step 9: Update CORS

After deploying the frontend, update the backend's `ALLOWED_ORIGINS`:

```bash
gcloud run services update medai-backend \
    --region=$GCP_REGION \
    --update-env-vars="ALLOWED_ORIGINS=https://medai-frontend-HASH-uc.a.run.app"
```

### Cost Estimate

| Resource | Monthly Cost |
|----------|-------------|
| Cloud SQL (db-f1-micro) | ~$7 |
| Cloud Run (backend, low traffic) | ~$0–5 |
| Cloud Run (frontend, low traffic) | ~$0–3 |
| Artifact Registry (storage) | ~$0.10/GB |
| **Total** | **~$7–15/month** |

All within the $300 free trial budget for several months.

---

## 3. Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | Yes | — | Anthropic API key for Claude |
| `DATABASE_URL` | Yes | `sqlite+aiosqlite:///./medai.db` | Async database URL |
| `JWT_SECRET` | Yes* | `CHANGE-ME-IN-PRODUCTION` | JWT signing secret |
| `ALLOWED_ORIGINS` | No | `http://localhost:3000` | CORS allowed origins (comma-separated) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `60` | JWT token expiry |
| `DEBUG` | No | `false` | Enable debug mode (mock AI tools) |
| `LOG_LEVEL` | No | `INFO` | Logging level |
| `ORCHESTRATOR_MODEL` | No | `claude-sonnet-4-5-20250929` | Claude model for orchestration |
| `ORCHESTRATOR_MAX_TOKENS` | No | `16384` | Max output tokens |
| `MEDGEMMA_4B_ENDPOINT` | No | `http://localhost:8010` | MedGemma 4B endpoint |
| `MEDGEMMA_27B_ENDPOINT` | No | `http://localhost:8011` | MedGemma 27B endpoint |
| `HEAR_ENDPOINT` | No | `http://localhost:8013` | HeAR audio endpoint |

\* Required in production. Has an insecure default for dev convenience.
