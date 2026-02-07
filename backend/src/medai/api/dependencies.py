"""FastAPI dependency injection — wiring the application together.

All service instances are created here and injected into route handlers.
This is the composition root of the application.
"""

from __future__ import annotations

from functools import lru_cache

from anthropic import AsyncAnthropic

from medai.config import Settings, get_settings
from medai.domain.interfaces import BaseJudge, BaseOrchestrator
from medai.services.judge import ClaudeJudge, MockJudge
from medai.services.orchestrator import ClaudeOrchestrator, MockOrchestrator
from medai.services.tool_registry import ToolRegistry
from medai.tools.mock import register_mock_tools


@lru_cache(maxsize=1)
def get_tool_registry() -> ToolRegistry:
    """Create and populate the tool registry (singleton)."""
    registry = ToolRegistry()
    # Register mock tools for development
    # TODO: Replace with real tools when Modal endpoints are ready
    for tool in register_mock_tools().values():
        registry.register(tool)
    return registry


@lru_cache(maxsize=1)
def get_anthropic_client() -> AsyncAnthropic:
    """Create the Anthropic client (singleton)."""
    settings = get_settings()
    return AsyncAnthropic(api_key=settings.anthropic_api_key)


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
