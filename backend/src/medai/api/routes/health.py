"""Health check endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from medai import __version__
from medai.api.dependencies import get_tool_registry
from medai.config import get_settings
from medai.domain.schemas import HealthResponse
from medai.services.tool_registry import ToolRegistry

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health_check(
    registry: ToolRegistry = Depends(get_tool_registry),
) -> HealthResponse:
    """API health check — returns status, version, and registered tools."""
    settings = get_settings()
    return HealthResponse(
        status="ok",
        version=__version__,
        tools_registered=[t.value for t in registry.list_tools()],
        debug=settings.debug,
    )
