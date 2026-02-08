"""FastAPI dependency injection — wiring the application together.

All service instances are created here and injected into route handlers.
This is the composition root of the application.
"""

from __future__ import annotations

from functools import lru_cache

from anthropic import AsyncAnthropic

from medai.config import Settings, get_settings
from medai.domain.entities import ToolName
from medai.domain.interfaces import (
    BaseJudge,
    BaseOrchestrator,
    BasePatientRepository,
    BaseReportRepository,
    BaseTimelineRepository,
)
from medai.repositories.memory import (
    InMemoryPatientRepository,
    InMemoryReportRepository,
    InMemoryTimelineRepository,
)
from medai.repositories.seed import create_seed_patients, create_seed_timeline_events
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
        # Override history_search with local in-memory implementation
        # (no external RAG endpoint needed for the hackathon prototype)
        timeline_repo = get_timeline_repository()
        tools[ToolName.HISTORY_SEARCH] = LocalHistorySearchTool(timeline_repo)

    for tool in tools.values():
        registry.register(tool)
    return registry


@lru_cache(maxsize=1)
def get_anthropic_client() -> AsyncAnthropic:
    """Create the Anthropic client (singleton)."""
    settings = get_settings()
    return AsyncAnthropic(api_key=settings.anthropic_api_key)


@lru_cache(maxsize=1)
def get_patient_repository() -> BasePatientRepository:
    """Create the patient repository (singleton).

    In DEBUG mode, seeds demo data automatically.
    TODO: Swap for SQLAlchemy repo when DB is ready.
    """
    repo = InMemoryPatientRepository()
    # Always seed demo patients (useful for demos + testing)
    repo.seed(create_seed_patients())
    return repo


@lru_cache(maxsize=1)
def get_timeline_repository() -> BaseTimelineRepository:
    """Create the timeline repository (singleton)."""
    repo = InMemoryTimelineRepository()
    # Always seed demo timeline events
    repo.seed(create_seed_timeline_events())
    return repo


@lru_cache(maxsize=1)
def get_report_repository() -> BaseReportRepository:
    """Create the report repository (singleton)."""
    return InMemoryReportRepository()


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
