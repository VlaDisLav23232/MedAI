"""Health check endpoint."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from medai import __version__
from medai.api.dependencies import get_tool_registry
from medai.config import get_settings
from medai.domain.schemas import HealthResponse
from medai.repositories.database import get_db_session
from medai.services.tool_registry import ToolRegistry

logger = structlog.get_logger()

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health_check(
    registry: ToolRegistry = Depends(get_tool_registry),
    session: AsyncSession = Depends(get_db_session),
) -> HealthResponse:
    """API health check — returns status, version, registered tools, and DB connectivity."""
    settings = get_settings()

    # Check database connectivity
    db_connected = True
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:
        logger.warning("health_check_db_failed", error=str(exc))
        db_connected = False

    return HealthResponse(
        status="ok",
        version=__version__,
        tools_registered=[t.value for t in registry.list_tools()],
        debug=settings.debug,
        db_connected=db_connected,
    )
