# ─── Multi-stage Dockerfile for MedAI Backend ──────────────
# Stage 1: Build dependencies in a virtualenv
# Stage 2: Copy only the virtualenv + source into slim runtime
# Result: ~150 MB image instead of ~800 MB

# ─── Builder ───────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Install system deps needed for building wheels (psycopg2, bcrypt, etc.)
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Create a virtualenv so we can copy it cleanly
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy project metadata first (for layer caching)
COPY pyproject.toml README.md ./
COPY src/ src/

# Install with [db] extras (includes sqlalchemy, alembic, asyncpg)
RUN pip install --no-cache-dir -e ".[db]"


# ─── Runtime ──────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# Install only the runtime C library (libpq for asyncpg)
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --gid 1000 medai && \
    useradd --uid 1000 --gid 1000 --create-home medai

# Copy virtualenv from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
WORKDIR /app
COPY --chown=medai:medai src/ src/
COPY --chown=medai:medai alembic/ alembic/
COPY --chown=medai:medai alembic.ini ./
COPY --chown=medai:medai pyproject.toml README.md ./

# Install the package in the runtime venv  
RUN pip install --no-cache-dir -e ".[db]"

USER medai

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import httpx; r = httpx.get('http://localhost:8000/api/v1/health'); r.raise_for_status()" || exit 1

CMD ["uvicorn", "medai.main:app", "--host", "0.0.0.0", "--port", "8000"]
