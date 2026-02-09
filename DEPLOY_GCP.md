# MedAI — Complete GCP Deployment Guide

Step-by-step instructions to deploy the entire MedAI stack on Google Cloud Platform
using the $300 free trial. Covers backend, frontend, database, secrets, GPU model
hosting, CI/CD, and cost management.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Prerequisites](#2-prerequisites)
3. [GCP Project Setup](#3-gcp-project-setup)
4. [Secret Manager — Store Credentials](#4-secret-manager--store-credentials)
5. [Cloud SQL — PostgreSQL Database](#5-cloud-sql--postgresql-database)
6. [Artifact Registry — Docker Images](#6-artifact-registry--docker-images)
7. [Build and Push Backend Image](#7-build-and-push-backend-image)
8. [Deploy Backend to Cloud Run](#8-deploy-backend-to-cloud-run)
9. [Run Database Migrations and Seed](#9-run-database-migrations-and-seed)
10. [Build and Push Frontend Image](#10-build-and-push-frontend-image)
11. [Deploy Frontend to Cloud Run](#11-deploy-frontend-to-cloud-run)
12. [Update CORS and Final Wiring](#12-update-cors-and-final-wiring)
13. [GPU Model Hosting](#13-gpu-model-hosting)
14. [CI/CD with Cloud Build](#14-cicd-with-cloud-build)
15. [Budget Alerts and Cost Controls](#15-budget-alerts-and-cost-controls)
16. [Monitoring and Logging](#16-monitoring-and-logging)
17. [Teardown — Delete Everything](#17-teardown--delete-everything)
18. [Cost Estimate](#18-cost-estimate)
19. [Troubleshooting](#19-troubleshooting)

---

## 1. Architecture Overview

```
                     HTTPS
  Users ──────────► Cloud Run (Frontend)
                       │
                       │ fetch /api/*
                       ▼
                    Cloud Run (Backend / FastAPI)
                       │
              ┌────────┼──────────┐
              ▼        ▼          ▼
         Cloud SQL   Secret     Modal.com (or GCE)
        (Postgres)   Manager    GPU Model Endpoints
                                  ├─ MedGemma 4B  (A10G)
                                  ├─ MedGemma 27B (A100)
                                  ├─ MedSigLIP    (T4)
                                  └─ HeAR         (T4)
```

| Component         | GCP Service         | Tier / Config           |
|-------------------|---------------------|-------------------------|
| Backend API       | Cloud Run           | 512 Mi / 1 vCPU         |
| Frontend          | Cloud Run           | 256 Mi / 1 vCPU         |
| Database          | Cloud SQL           | db-f1-micro, 10 GB SSD  |
| Docker images     | Artifact Registry   | Standard repo           |
| Secrets           | Secret Manager      | Per-secret pricing       |
| GPU inference     | Modal (recommended) | Serverless GPUs          |

---

## 2. Prerequisites

### 2.1 Google Cloud Account

1. Go to [cloud.google.com](https://cloud.google.com/) and sign up.
2. You will get **$300 in free credits** valid for 90 days.
3. A credit card is required but will not be charged unless you upgrade.

### 2.2 Install gcloud CLI (macOS)

```bash
# Option A: Homebrew (recommended)
brew install --cask google-cloud-sdk

# Option B: Official installer
curl https://sdk.cloud.google.com | bash
exec -l $SHELL   # restart shell to pick up PATH
```

Verify installation:

```bash
gcloud version
# Google Cloud SDK 5xx.x.x (any recent version works)
```

### 2.3 Install Docker

Download and install [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/).
Ensure it is running before building images.

### 2.4 Required API Keys

You will need:

| Key                  | Where to get it                                      |
|----------------------|------------------------------------------------------|
| `ANTHROPIC_API_KEY`  | [console.anthropic.com](https://console.anthropic.com) |
| `HF_TOKEN`           | [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) (for GPU models) |

### 2.5 Clone the Repository

```bash
git clone https://github.com/YOUR_ORG/Agentic-MedAI-SoftServe.git
cd Agentic-MedAI-SoftServe
```

---

## 3. GCP Project Setup

### 3.1 Authenticate and Create a Project

```bash
# Log in to GCP
gcloud auth login

# Create a new project (or use an existing one)
gcloud projects create medai-prod --name="MedAI Production"

# Set it as the active project
gcloud config set project medai-prod

# Link billing account (required)
# List your billing accounts:
gcloud billing accounts list

# Link (replace BILLING_ACCOUNT_ID with the ID from above):
gcloud billing projects link medai-prod --billing-account=BILLING_ACCOUNT_ID
```

### 3.2 Set Shell Variables

These variables are used throughout the guide. Set them once:

```bash
export GCP_PROJECT=medai-prod
export GCP_REGION=us-central1
export GCP_ZONE=us-central1-a
export SQL_INSTANCE=medai-db
export AR_REPO=medai-repo
export BACKEND_SERVICE=medai-backend
export FRONTEND_SERVICE=medai-frontend
```

> Tip: Add these to your `~/.zshrc` or a `gcp-env.sh` file and source it.

### 3.3 Enable Required APIs

```bash
gcloud services enable \
    sqladmin.googleapis.com \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    secretmanager.googleapis.com \
    compute.googleapis.com \
    iam.googleapis.com
```

This takes about 30 seconds. All these APIs are either free or pay-per-use.

---

## 4. Secret Manager — Store Credentials

Never put secrets directly in Cloud Run environment variables. Use Secret Manager.

### 4.1 Create Secrets

```bash
# Anthropic API key
echo -n "sk-ant-YOUR_ACTUAL_KEY" | \
    gcloud secrets create anthropic-api-key --data-file=-

# JWT secret (generate a strong random one)
openssl rand -base64 32 | \
    gcloud secrets create jwt-secret --data-file=-

# Database password (generate and save)
DB_PASSWORD=$(openssl rand -base64 24)
echo -n "$DB_PASSWORD" | \
    gcloud secrets create db-password --data-file=-

# Print the DB password so you can use it in the next step
echo "Database password: $DB_PASSWORD"
```

### 4.2 Grant Cloud Run Access to Secrets

Cloud Run uses the default Compute Engine service account. Grant it access:

```bash
# Get the project number
PROJECT_NUMBER=$(gcloud projects describe $GCP_PROJECT --format="value(projectNumber)")

# Grant Secret Manager access to the default compute service account
gcloud secrets add-iam-policy-binding anthropic-api-key \
    --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding jwt-secret \
    --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding db-password \
    --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

### 4.3 Verify Secrets

```bash
gcloud secrets list
# Should show: anthropic-api-key, jwt-secret, db-password

# Read a secret value (to verify)
gcloud secrets versions access latest --secret=jwt-secret
```

---

## 5. Cloud SQL — PostgreSQL Database

### 5.1 Create the Instance

```bash
gcloud sql instances create $SQL_INSTANCE \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=$GCP_REGION \
    --storage-size=10GB \
    --storage-auto-increase \
    --availability-type=zonal \
    --no-backup
```

This takes 3-5 minutes. The `db-f1-micro` tier costs approximately $7/month.

> Note: `--no-backup` saves cost. For production, remove this flag to enable
> automated backups ($0.08/GB/month).

### 5.2 Set the User Password

Use the same password you stored in Secret Manager:

```bash
gcloud sql users set-password postgres \
    --instance=$SQL_INSTANCE \
    --password="$DB_PASSWORD"
```

### 5.3 Create the Database

```bash
gcloud sql databases create medai --instance=$SQL_INSTANCE
```

### 5.4 Get the Connection Name

```bash
export SQL_CONNECTION=$(gcloud sql instances describe $SQL_INSTANCE \
    --format="value(connectionName)")

echo "Connection name: $SQL_CONNECTION"
# Output: medai-prod:us-central1:medai-db
```

Save this value — you will use it when deploying Cloud Run.

### 5.5 Grant Cloud SQL Client Role

```bash
gcloud projects add-iam-policy-binding $GCP_PROJECT \
    --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
    --role="roles/cloudsql.client"
```

---

## 6. Artifact Registry — Docker Images

### 6.1 Create the Repository

```bash
gcloud artifacts repositories create $AR_REPO \
    --repository-format=docker \
    --location=$GCP_REGION \
    --description="MedAI Docker images"
```

### 6.2 Configure Docker Authentication

```bash
gcloud auth configure-docker ${GCP_REGION}-docker.pkg.dev
```

This adds the Artifact Registry domain to Docker's credential helpers.

---

## 7. Build and Push Backend Image

### 7.1 Build Locally

```bash
cd backend

docker build \
    -t ${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT}/${AR_REPO}/medai-backend:latest \
    -t ${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT}/${AR_REPO}/medai-backend:v1 \
    .
```

### 7.2 Push to Artifact Registry

```bash
docker push ${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT}/${AR_REPO}/medai-backend:latest
docker push ${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT}/${AR_REPO}/medai-backend:v1

cd ..
```

### 7.3 Alternative: Build with Cloud Build (no local Docker needed)

```bash
cd backend

gcloud builds submit \
    --tag ${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT}/${AR_REPO}/medai-backend:latest \
    .

cd ..
```

Cloud Build runs the Docker build on GCP's servers. First 120 build-minutes/day are free.

---

## 8. Deploy Backend to Cloud Run

### 8.1 Deploy the Service

```bash
gcloud run deploy $BACKEND_SERVICE \
    --image=${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT}/${AR_REPO}/medai-backend:latest \
    --region=$GCP_REGION \
    --platform=managed \
    --allow-unauthenticated \
    --port=8000 \
    --memory=512Mi \
    --cpu=1 \
    --min-instances=0 \
    --max-instances=3 \
    --timeout=300 \
    --add-cloudsql-instances=$SQL_CONNECTION \
    --set-secrets="ANTHROPIC_API_KEY=anthropic-api-key:latest,JWT_SECRET=jwt-secret:latest" \
    --set-env-vars="\
DATABASE_URL=postgresql+asyncpg://postgres:${DB_PASSWORD}@/medai?host=/cloudsql/${SQL_CONNECTION},\
ALLOWED_ORIGINS=http://localhost:3000,\
DEBUG=false,\
LOG_LEVEL=INFO,\
MEDGEMMA_4B_ENDPOINT=https://YOUR_MODAL_USERNAME--medai-medgemma-4b-medgemma4b-predict.modal.run,\
MEDGEMMA_27B_ENDPOINT=https://YOUR_MODAL_USERNAME--medai-medgemma-27b-medgemma27b-predict.modal.run,\
MEDSIGLIP_ENDPOINT=https://YOUR_MODAL_USERNAME--medai-siglip-explainability-siglipexplainability-explain.modal.run,\
HEAR_ENDPOINT=https://YOUR_MODAL_USERNAME--medai-hear-audio-hearaudio-predict.modal.run"
```

> **Database URL format for Cloud Run + Cloud SQL:**
> Cloud Run connects to Cloud SQL via a Unix socket mounted at `/cloudsql/CONNECTION_NAME`.
> The format is: `postgresql+asyncpg://user:password@/dbname?host=/cloudsql/CONNECTION_NAME`
>
> Note the `@/` (no host) and the `?host=/cloudsql/...` query parameter.

### 8.2 Get the Backend URL

```bash
export BACKEND_URL=$(gcloud run services describe $BACKEND_SERVICE \
    --region=$GCP_REGION \
    --format="value(status.url)")

echo "Backend URL: $BACKEND_URL"
# Example: https://medai-backend-abc123-uc.a.run.app
```

### 8.3 Verify the Backend

```bash
curl ${BACKEND_URL}/api/v1/health
# Expected: {"status":"healthy"}

# Check API docs
open ${BACKEND_URL}/docs
```

---

## 9. Run Database Migrations and Seed

### 9.1 Run Alembic Migrations

```bash
gcloud run jobs create medai-migrate \
    --image=${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT}/${AR_REPO}/medai-backend:latest \
    --region=$GCP_REGION \
    --add-cloudsql-instances=$SQL_CONNECTION \
    --set-secrets="ANTHROPIC_API_KEY=anthropic-api-key:latest" \
    --set-env-vars="DATABASE_URL=postgresql+asyncpg://postgres:${DB_PASSWORD}@/medai?host=/cloudsql/${SQL_CONNECTION}" \
    --command="alembic" \
    --args="upgrade,head" \
    --max-retries=0

gcloud run jobs execute medai-migrate --region=$GCP_REGION --wait
```

Check the output:

```bash
gcloud run jobs executions list --job=medai-migrate --region=$GCP_REGION
```

### 9.2 Seed Demo Data

```bash
gcloud run jobs create medai-seed \
    --image=${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT}/${AR_REPO}/medai-backend:latest \
    --region=$GCP_REGION \
    --add-cloudsql-instances=$SQL_CONNECTION \
    --set-secrets="ANTHROPIC_API_KEY=anthropic-api-key:latest" \
    --set-env-vars="DATABASE_URL=postgresql+asyncpg://postgres:${DB_PASSWORD}@/medai?host=/cloudsql/${SQL_CONNECTION}" \
    --command="python" \
    --args="-m,medai.cli.seed" \
    --max-retries=0

gcloud run jobs execute medai-seed --region=$GCP_REGION --wait
```

### 9.3 Alternative: Local Migrations via Cloud SQL Proxy

If Cloud Run jobs give you trouble, run migrations locally:

```bash
# Install Cloud SQL Auth Proxy
# macOS:
brew install cloud-sql-proxy

# Start the proxy (connects to your Cloud SQL instance)
cloud-sql-proxy $SQL_CONNECTION &
PROXY_PID=$!

# Run migrations against the proxy
cd backend
DATABASE_URL="postgresql+asyncpg://postgres:${DB_PASSWORD}@127.0.0.1:5432/medai" \
    alembic upgrade head

# Seed data
DATABASE_URL="postgresql+asyncpg://postgres:${DB_PASSWORD}@127.0.0.1:5432/medai" \
    ANTHROPIC_API_KEY=dummy \
    python -m medai.cli.seed

cd ..

# Stop the proxy
kill $PROXY_PID
```

### 9.4 Default Login Credentials

After seeding, these accounts are available:

| User   | Email              | Password   | Role   |
|--------|--------------------|------------|--------|
| Admin  | admin@medai.com    | admin123   | admin  |
| Doctor | doctor@medai.com   | doctor123  | doctor |

---

## 10. Build and Push Frontend Image

### 10.1 Build with Backend URL Baked In

The `NEXT_PUBLIC_API_URL` must be set at build time (Next.js inlines it):

```bash
cd frontend

docker build \
    --build-arg NEXT_PUBLIC_API_URL=$BACKEND_URL \
    -t ${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT}/${AR_REPO}/medai-frontend:latest \
    -t ${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT}/${AR_REPO}/medai-frontend:v1 \
    .
```

### 10.2 Push to Artifact Registry

```bash
docker push ${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT}/${AR_REPO}/medai-frontend:latest
docker push ${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT}/${AR_REPO}/medai-frontend:v1

cd ..
```

### 10.3 Alternative: Build with Cloud Build

```bash
cd frontend

gcloud builds submit \
    --tag ${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT}/${AR_REPO}/medai-frontend:latest \
    --substitutions=_NEXT_PUBLIC_API_URL=$BACKEND_URL \
    .

cd ..
```

> Note: If using Cloud Build, you need a `cloudbuild.yaml` that passes the build arg.
> See [Section 14](#14-cicd-with-cloud-build) for the full CI/CD setup.

---

## 11. Deploy Frontend to Cloud Run

```bash
gcloud run deploy $FRONTEND_SERVICE \
    --image=${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT}/${AR_REPO}/medai-frontend:latest \
    --region=$GCP_REGION \
    --platform=managed \
    --allow-unauthenticated \
    --port=3000 \
    --memory=256Mi \
    --cpu=1 \
    --min-instances=0 \
    --max-instances=2
```

Get the frontend URL:

```bash
export FRONTEND_URL=$(gcloud run services describe $FRONTEND_SERVICE \
    --region=$GCP_REGION \
    --format="value(status.url)")

echo "Frontend URL: $FRONTEND_URL"
```

Open it in your browser:

```bash
open $FRONTEND_URL
```

---

## 12. Update CORS and Final Wiring

Now that you have the frontend URL, update the backend's CORS setting:

```bash
gcloud run services update $BACKEND_SERVICE \
    --region=$GCP_REGION \
    --update-env-vars="ALLOWED_ORIGINS=${FRONTEND_URL}"
```

### Verify End-to-End

1. Open `$FRONTEND_URL` in your browser.
2. Log in with `admin@medai.com` / `admin123`.
3. Create a case and verify the pipeline runs.

---

## 13. GPU Model Hosting

The MedAI pipeline uses four AI models that require GPU acceleration:

| Model          | GPU Required | VRAM     | Use Case                   |
|----------------|-------------|----------|----------------------------|
| MedGemma 4B    | A10G        | ~12 GB   | Medical image + text        |
| MedGemma 27B   | A100-80GB   | ~60 GB   | Clinical text reasoning     |
| MedSigLIP      | T4          | ~2 GB    | Image explainability        |
| HeAR           | T4          | ~2 GB    | Audio health analysis       |

### Option A: Keep Modal (Recommended for $300 budget)

Modal provides serverless GPU inference with pay-per-second billing. This is
by far the cheapest option for a demo/dev deployment.

**Cost**: You only pay when models are actively processing requests.
Modal free tier includes $30/month in compute credits.

```bash
# 1. Install Modal CLI
pip install modal

# 2. Authenticate
modal setup

# 3. Create HuggingFace secret (for downloading gated models)
modal secret create huggingface-secret HF_TOKEN=hf_YOUR_TOKEN

# 4. Deploy all model endpoints
bash deploy/modal/deploy_all.sh

# 5. Get your endpoint URLs from the Modal dashboard
open https://modal.com/apps
```

After deployment, Modal prints endpoint URLs like:
```
MEDGEMMA_4B_ENDPOINT=https://your-username--medai-medgemma-4b-medgemma4b-predict.modal.run
MEDGEMMA_27B_ENDPOINT=https://your-username--medai-medgemma-27b-medgemma27b-predict.modal.run
MEDSIGLIP_ENDPOINT=https://your-username--medai-siglip-explainability-siglipexplainability-explain.modal.run
HEAR_ENDPOINT=https://your-username--medai-hear-audio-hearaudio-predict.modal.run
```

Update your Cloud Run backend with these URLs:

```bash
gcloud run services update $BACKEND_SERVICE \
    --region=$GCP_REGION \
    --update-env-vars="\
MEDGEMMA_4B_ENDPOINT=https://your-username--medai-medgemma-4b-medgemma4b-predict.modal.run,\
MEDGEMMA_27B_ENDPOINT=https://your-username--medai-medgemma-27b-medgemma27b-predict.modal.run,\
MEDSIGLIP_ENDPOINT=https://your-username--medai-siglip-explainability-siglipexplainability-explain.modal.run,\
HEAR_ENDPOINT=https://your-username--medai-hear-audio-hearaudio-predict.modal.run"
```

### Option B: Self-Host on GCP Compute Engine

> Warning: GPU VMs are expensive ($0.35-$2.48/hour) and will burn through your
> $300 free trial quickly. New GCP accounts have **zero GPU quota** by default
> and must request an increase, which can take 24-48 hours to approve.

#### Step 1: Request GPU Quota

```bash
# Check current GPU quota
gcloud compute regions describe $GCP_REGION \
    --format="table(quotas.filter(metric:NVIDIA))"
```

If all GPU quotas show `0`, request an increase:

1. Go to [IAM & Admin > Quotas](https://console.cloud.google.com/iam-admin/quotas).
2. Filter by "GPUs (all regions)" or the specific GPU type (T4, A100, etc.).
3. Select the quota, click "Edit Quotas", request 1-2 GPUs.
4. Provide a justification (e.g., "ML model inference for medical AI research").
5. Wait for approval (typically 24-48 hours for free trial accounts).

#### Step 2: Create a GPU VM (Example: T4 for MedSigLIP + HeAR)

```bash
gcloud compute instances create medai-gpu-t4 \
    --zone=$GCP_ZONE \
    --machine-type=n1-standard-4 \
    --accelerator=type=nvidia-tesla-t4,count=1 \
    --image-family=pytorch-latest-gpu \
    --image-project=deeplearning-platform-release \
    --boot-disk-size=100GB \
    --maintenance-policy=TERMINATE \
    --metadata="install-nvidia-driver=True"
```

Estimated cost: T4 VM = ~$0.35/hour = ~$252/month (will exceed free trial quickly).

#### Step 3: Deploy Models on the VM

```bash
# SSH into the VM
gcloud compute ssh medai-gpu-t4 --zone=$GCP_ZONE

# Inside the VM: clone repo, install deps, run model server
git clone https://github.com/YOUR_ORG/Agentic-MedAI-SoftServe.git
cd Agentic-MedAI-SoftServe

pip install torch transformers accelerate
# Run each model as a FastAPI service on different ports
# (You would need to adapt the Modal deployment scripts to standalone FastAPI)
```

**Recommendation**: Use Modal (Option A) for the $300 free trial. It is significantly
cheaper for intermittent usage and requires no VM management.

---

## 14. CI/CD with Cloud Build

### 14.1 Create Cloud Build Configuration

Create this file at the repository root:

```yaml
# cloudbuild.yaml
steps:
  # ── Build and push backend ───────────────────────────────
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'build'
      - '-t'
      - '${_REGION}-docker.pkg.dev/$PROJECT_ID/${_AR_REPO}/medai-backend:$COMMIT_SHA'
      - '-t'
      - '${_REGION}-docker.pkg.dev/$PROJECT_ID/${_AR_REPO}/medai-backend:latest'
      - './backend'
    id: build-backend

  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'push'
      - '${_REGION}-docker.pkg.dev/$PROJECT_ID/${_AR_REPO}/medai-backend:$COMMIT_SHA'
    id: push-backend
    waitFor: ['build-backend']

  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'push'
      - '${_REGION}-docker.pkg.dev/$PROJECT_ID/${_AR_REPO}/medai-backend:latest'
    waitFor: ['build-backend']

  # ── Deploy backend to Cloud Run ──────────────────────────
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - '${_BACKEND_SERVICE}'
      - '--image=${_REGION}-docker.pkg.dev/$PROJECT_ID/${_AR_REPO}/medai-backend:$COMMIT_SHA'
      - '--region=${_REGION}'
      - '--platform=managed'
    id: deploy-backend
    waitFor: ['push-backend']

  # ── Build and push frontend ──────────────────────────────
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'build'
      - '--build-arg'
      - 'NEXT_PUBLIC_API_URL=${_BACKEND_URL}'
      - '-t'
      - '${_REGION}-docker.pkg.dev/$PROJECT_ID/${_AR_REPO}/medai-frontend:$COMMIT_SHA'
      - '-t'
      - '${_REGION}-docker.pkg.dev/$PROJECT_ID/${_AR_REPO}/medai-frontend:latest'
      - './frontend'
    id: build-frontend

  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'push'
      - '${_REGION}-docker.pkg.dev/$PROJECT_ID/${_AR_REPO}/medai-frontend:$COMMIT_SHA'
    id: push-frontend
    waitFor: ['build-frontend']

  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'push'
      - '${_REGION}-docker.pkg.dev/$PROJECT_ID/${_AR_REPO}/medai-frontend:latest'
    waitFor: ['build-frontend']

  # ── Deploy frontend to Cloud Run ─────────────────────────
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - '${_FRONTEND_SERVICE}'
      - '--image=${_REGION}-docker.pkg.dev/$PROJECT_ID/${_AR_REPO}/medai-frontend:$COMMIT_SHA'
      - '--region=${_REGION}'
      - '--platform=managed'
    waitFor: ['push-frontend']

substitutions:
  _REGION: us-central1
  _AR_REPO: medai-repo
  _BACKEND_SERVICE: medai-backend
  _FRONTEND_SERVICE: medai-frontend
  _BACKEND_URL: https://medai-backend-REPLACE-uc.a.run.app

images:
  - '${_REGION}-docker.pkg.dev/$PROJECT_ID/${_AR_REPO}/medai-backend:$COMMIT_SHA'
  - '${_REGION}-docker.pkg.dev/$PROJECT_ID/${_AR_REPO}/medai-frontend:$COMMIT_SHA'

options:
  logging: CLOUD_LOGGING_ONLY
```

### 14.2 Create a Build Trigger

```bash
# Connect your GitHub repository first
# Go to: https://console.cloud.google.com/cloud-build/triggers
# Click "Connect Repository" and follow the OAuth flow

# Then create a trigger for pushes to main:
gcloud builds triggers create github \
    --repo-name=Agentic-MedAI-SoftServe \
    --repo-owner=YOUR_GITHUB_ORG \
    --branch-pattern="^main$" \
    --build-config=cloudbuild.yaml \
    --substitutions=_BACKEND_URL=$BACKEND_URL
```

### 14.3 Grant Cloud Build Permissions

Cloud Build needs permission to deploy to Cloud Run:

```bash
# Grant Cloud Run Admin role
gcloud projects add-iam-policy-binding $GCP_PROJECT \
    --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
    --role="roles/run.admin"

# Grant Service Account User role (to act as the compute service account)
gcloud iam service-accounts add-iam-policy-binding \
    ${PROJECT_NUMBER}-compute@developer.gserviceaccount.com \
    --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
    --role="roles/iam.serviceAccountUser"
```

### 14.4 Test the Pipeline

```bash
# Trigger a manual build
gcloud builds submit --config=cloudbuild.yaml \
    --substitutions=COMMIT_SHA=manual-test,_BACKEND_URL=$BACKEND_URL
```

---

## 15. Budget Alerts and Cost Controls

### 15.1 Set a Budget Alert

```bash
# Via the Console (easier):
# 1. Go to Billing > Budgets & alerts
# 2. Create a budget:
#    - Name: "MedAI Free Trial Budget"
#    - Amount: $50 (or whatever threshold you want)
#    - Alert thresholds: 50%, 80%, 100%
#    - Email notifications: your email
```

Or use the API:

```bash
open "https://console.cloud.google.com/billing/budgets?project=$GCP_PROJECT"
```

### 15.2 Recommended Budget Breakpoints

| Alert At | Meaning                                     |
|----------|---------------------------------------------|
| $50      | ~17% of trial used — check if spending is expected |
| $100     | ~33% of trial — review GPU/Cloud SQL costs   |
| $200     | ~67% of trial — consider scaling down         |
| $280     | ~93% of trial — stop GPU VMs if running       |

### 15.3 Quick Cost Check

```bash
# View current billing
open "https://console.cloud.google.com/billing/overview?project=$GCP_PROJECT"

# List running Cloud Run services and their traffic
gcloud run services list --region=$GCP_REGION

# Check if any Compute Engine VMs are running (GPU costs)
gcloud compute instances list
```

### 15.4 Emergency Cost Reduction

If you are burning through credits too fast:

```bash
# Stop GPU VMs immediately
gcloud compute instances stop medai-gpu-t4 --zone=$GCP_ZONE

# Scale Cloud Run to zero min-instances (only runs on requests)
gcloud run services update $BACKEND_SERVICE --region=$GCP_REGION --min-instances=0
gcloud run services update $FRONTEND_SERVICE --region=$GCP_REGION --min-instances=0

# (Nuclear option) Delete Cloud SQL to stop the ~$7/month charge
# gcloud sql instances delete $SQL_INSTANCE
```

---

## 16. Monitoring and Logging

### 16.1 View Cloud Run Logs

```bash
# Backend logs (live tail)
gcloud run services logs tail $BACKEND_SERVICE --region=$GCP_REGION

# Frontend logs
gcloud run services logs tail $FRONTEND_SERVICE --region=$GCP_REGION

# Or read recent logs
gcloud run services logs read $BACKEND_SERVICE --region=$GCP_REGION --limit=100
```

### 16.2 Cloud Console Dashboards

```bash
# Cloud Run dashboard
open "https://console.cloud.google.com/run?project=$GCP_PROJECT"

# Cloud SQL monitoring
open "https://console.cloud.google.com/sql/instances/$SQL_INSTANCE/overview?project=$GCP_PROJECT"

# Error Reporting
open "https://console.cloud.google.com/errors?project=$GCP_PROJECT"
```

### 16.3 Health Check

Quick script to verify all services:

```bash
echo "=== Backend Health ==="
curl -s ${BACKEND_URL}/api/v1/health | python3 -m json.tool

echo ""
echo "=== Frontend ==="
curl -s -o /dev/null -w "HTTP %{http_code}" ${FRONTEND_URL}
echo ""

echo ""
echo "=== Cloud SQL ==="
gcloud sql instances describe $SQL_INSTANCE --format="value(state)"
```

---

## 17. Teardown — Delete Everything

When you are done or want to start fresh:

```bash
# Delete Cloud Run services
gcloud run services delete $BACKEND_SERVICE --region=$GCP_REGION --quiet
gcloud run services delete $FRONTEND_SERVICE --region=$GCP_REGION --quiet

# Delete Cloud Run jobs
gcloud run jobs delete medai-migrate --region=$GCP_REGION --quiet
gcloud run jobs delete medai-seed --region=$GCP_REGION --quiet

# Delete Cloud SQL instance (stops ~$7/month billing)
gcloud sql instances delete $SQL_INSTANCE --quiet

# Delete Docker images
gcloud artifacts repositories delete $AR_REPO \
    --location=$GCP_REGION --quiet

# Delete secrets
gcloud secrets delete anthropic-api-key --quiet
gcloud secrets delete jwt-secret --quiet
gcloud secrets delete db-password --quiet

# Delete GPU VMs (if created)
gcloud compute instances delete medai-gpu-t4 --zone=$GCP_ZONE --quiet

# (Optional) Delete the entire project
# gcloud projects delete $GCP_PROJECT
```

---

## 18. Cost Estimate

### Monthly Costs (Light Usage — Demo/Dev)

| Resource                        | Tier / Config      | Monthly Cost |
|---------------------------------|--------------------|--------------|
| Cloud SQL PostgreSQL            | db-f1-micro, 10 GB | ~$7.00       |
| Cloud Run — Backend             | 512 Mi, 0-3 inst   | ~$0-5.00     |
| Cloud Run — Frontend            | 256 Mi, 0-2 inst   | ~$0-3.00     |
| Artifact Registry               | Image storage      | ~$0.10/GB    |
| Secret Manager                  | 3 secrets          | ~$0.18       |
| Cloud Build                     | 120 min/day free   | $0.00        |
| GPU Models (Modal)              | Pay-per-second     | ~$0-10.00    |
| **Total (without self-hosted GPU)** |                | **~$7-25/month** |

### $300 Free Trial Duration

| Scenario                | Estimated Duration |
|-------------------------|-------------------|
| Cloud Run + Cloud SQL only (Modal GPUs) | ~12-40 months (exceeds 90-day trial period) |
| + T4 GPU VM running 24/7 | ~5 weeks          |
| + A100 GPU VM running 24/7 | ~5 days           |

The free trial expires after 90 days regardless of remaining credits.

---

## 19. Troubleshooting

### "Connection refused" to Cloud SQL

```
sqlalchemy.exc.OperationalError: could not connect to server
```

**Fix**: Ensure the Cloud SQL connection name is correct and the service account
has `roles/cloudsql.client`:

```bash
echo $SQL_CONNECTION
gcloud run services describe $BACKEND_SERVICE --region=$GCP_REGION \
    --format="value(spec.template.metadata.annotations['run.googleapis.com/cloudsql-instances'])"
```

These should match. If not, redeploy with the correct `--add-cloudsql-instances`.

### "Permission denied" accessing secrets

```
google.api_core.exceptions.PermissionDenied: 403
```

**Fix**: Grant the secret accessor role:

```bash
gcloud secrets add-iam-policy-binding SECRET_NAME \
    --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

### Frontend returns 502 Bad Gateway

The frontend container may have crashed. Check logs:

```bash
gcloud run services logs read $FRONTEND_SERVICE --region=$GCP_REGION --limit=50
```

Common causes:
- `NEXT_PUBLIC_API_URL` was not set at build time (must be a build arg, not runtime env var).
- Memory too low — increase to 512Mi: `gcloud run services update $FRONTEND_SERVICE --memory=512Mi --region=$GCP_REGION`

### Cloud Run cold starts are slow

```bash
# Set minimum 1 instance to eliminate cold starts (costs ~$5-10/month more)
gcloud run services update $BACKEND_SERVICE --region=$GCP_REGION --min-instances=1
```

### GPU quota is zero

New GCP accounts have zero GPU quota. You must request an increase:

1. Go to [Quotas page](https://console.cloud.google.com/iam-admin/quotas).
2. Filter: `metric:gpus`.
3. Select the GPU type and region.
4. Click "Edit Quotas" and request 1.
5. Wait 24-48 hours for approval.

### Database migration fails

If `medai-migrate` job fails:

```bash
# Check job logs
gcloud run jobs executions describe \
    $(gcloud run jobs executions list --job=medai-migrate --region=$GCP_REGION --format="value(name)" --limit=1) \
    --region=$GCP_REGION
```

Common fix — use Cloud SQL Proxy locally (see [Section 9.3](#93-alternative-local-migrations-via-cloud-sql-proxy)).

### How to update environment variables

```bash
# Add or update a single variable
gcloud run services update $BACKEND_SERVICE \
    --region=$GCP_REGION \
    --update-env-vars="KEY=value"

# Update multiple variables
gcloud run services update $BACKEND_SERVICE \
    --region=$GCP_REGION \
    --update-env-vars="KEY1=val1,KEY2=val2"

# Remove a variable
gcloud run services update $BACKEND_SERVICE \
    --region=$GCP_REGION \
    --remove-env-vars="OLD_KEY"
```
