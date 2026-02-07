"""FastAPI application entry point.

Assembles routers, middleware, and startup/shutdown hooks.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from medai import __version__
from medai.api.routes import health, cases
from medai.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifecycle — startup and shutdown hooks."""
    logger = structlog.get_logger()
    settings = get_settings()

    logger.info(
        "starting_medai_backend",
        version=__version__,
        debug=settings.debug,
        model=settings.orchestrator_model,
    )

    yield  # App is running

    logger.info("shutting_down_medai_backend")


def create_app() -> FastAPI:
    """Application factory — creates and configures the FastAPI app."""
    settings = get_settings()

    app = FastAPI(
        title="MedAI — Agentic Medical AI Assistant",
        description=(
            "End-to-end medical AI backend with Claude orchestration, "
            "MedGemma specialist tools, and explainable AI reports."
        ),
        version=__version__,
        lifespan=lifespan,
        debug=settings.debug,
    )

    # ── CORS (allow frontend) ──────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Restrict in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routes ─────────────────────────────────────────────
    app.include_router(health.router, prefix="/api/v1")
    app.include_router(cases.router, prefix="/api/v1")

    return app


# Module-level app instance for uvicorn
app = create_app()
