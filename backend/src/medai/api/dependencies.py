"""FastAPI dependency injection — wiring the application together.

All service instances are created here and injected into route handlers.
This is the composition root of the application.

Repository dependencies use per-request AsyncSession from the database
module — no more singletons for repos.
"""

from __future__ import annotations

from functools import lru_cache

from anthropic import AsyncAnthropic
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from medai.config import Settings, get_settings
from medai.domain.entities import ToolName
from medai.domain.interfaces import (
    BaseJudge,
    BaseOrchestrator,
    BasePatientRepository,
    BaseReportRepository,
    BaseTimelineRepository,
    BaseUserRepository,
)
from medai.repositories.database import get_db_session
from medai.repositories.sqlalchemy import (
    SqlAlchemyPatientRepository,
    SqlAlchemyReportRepository,
    SqlAlchemyTimelineRepository,
    SqlAlchemyUserRepository,
)
from medai.services.judge import ClaudeJudge, MockJudge
from medai.services.orchestrator import ClaudeOrchestrator, MockOrchestrator
from medai.services.tool_registry import ToolRegistry
from medai.tools.http import register_http_tools
from medai.tools.local import LocalHistorySearchTool
from medai.tools.mock import register_mock_tools


@lru_cache(maxsize=1)
def get_tool_registry() -> ToolRegistry:
    """Create and populate the tool registry (singleton).

    DEBUG=true  → mock tools (no GPU needed)
    DEBUG=false → HTTP tools calling real model endpoints
                  + LocalHistorySearchTool (in-memory timeline search)
    """
    settings = get_settings()
    registry = ToolRegistry()

    if settings.debug:
        tools = register_mock_tools()
    else:
        tools = register_http_tools(settings)
        # History search uses in-memory for now — will be wired to DB later
        # when the tool is refactored to accept a session-scoped repo.
        # For now, we skip it in non-debug mode if no timeline repo is available.

    for tool in tools.values():
        registry.register(tool)
    return registry


@lru_cache(maxsize=1)
def get_anthropic_client() -> AsyncAnthropic:
    """Create the Anthropic client (singleton)."""
    settings = get_settings()
    return AsyncAnthropic(api_key=settings.anthropic_api_key)


# ── Per-request repository dependencies ────────────────────

def get_patient_repository(
    session: AsyncSession = Depends(get_db_session),
) -> BasePatientRepository:
    """Per-request patient repository backed by PostgreSQL."""
    return SqlAlchemyPatientRepository(session)


def get_timeline_repository(
    session: AsyncSession = Depends(get_db_session),
) -> BaseTimelineRepository:
    """Per-request timeline repository backed by PostgreSQL."""
    return SqlAlchemyTimelineRepository(session)


def get_report_repository(
    session: AsyncSession = Depends(get_db_session),
) -> BaseReportRepository:
    """Per-request report repository backed by PostgreSQL."""
    return SqlAlchemyReportRepository(session)


def get_user_repository(
    session: AsyncSession = Depends(get_db_session),
) -> BaseUserRepository:
    """Per-request user repository backed by PostgreSQL."""
    return SqlAlchemyUserRepository(session)


def get_judge() -> BaseJudge:
    """Create the judge agent."""
    settings = get_settings()
    if settings.debug:
        return MockJudge()
    client = get_anthropic_client()
    return ClaudeJudge(client=client, settings=settings)


def get_orchestrator() -> BaseOrchestrator:
    """Create the orchestrator."""
    settings = get_settings()
    registry = get_tool_registry()
    judge = get_judge()

    if settings.debug:
        return MockOrchestrator(tool_registry=registry, judge=judge)

    client = get_anthropic_client()
    return ClaudeOrchestrator(
        client=client,
        settings=settings,
        tool_registry=registry,
        judge=judge,
    )
