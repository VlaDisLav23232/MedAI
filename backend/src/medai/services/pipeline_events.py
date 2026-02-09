"""Pipeline event bus — delivers real-time progress events to consumers.

Uses ``contextvars`` so each request gets its own isolated queue.
The SSE endpoint sets a queue before calling the orchestrator;
the orchestrator (and its tools) call ``emit_pipeline_event()``
which pushes to that queue — zero coupling between layers.

Usage in the orchestrator / tools::

    from medai.services.pipeline_events import emit_pipeline_event
    await emit_pipeline_event("tool_start", tool="image_analysis")

Usage in the SSE endpoint::

    from medai.services.pipeline_events import create_event_queue, pipeline_events_var
    queue = create_event_queue()
    token = pipeline_events_var.set(queue)
    try:
        ...run orchestrator...
    finally:
        pipeline_events_var.reset(token)
"""

from __future__ import annotations

import asyncio
import contextvars
import json
import time
from typing import Any

# Per-request event queue (None when no consumer is listening)
pipeline_events_var: contextvars.ContextVar[asyncio.Queue[dict[str, Any]] | None] = (
    contextvars.ContextVar("pipeline_events", default=None)
)


def create_event_queue() -> asyncio.Queue[dict[str, Any]]:
    """Create a fresh event queue for a single request."""
    return asyncio.Queue()


async def emit_pipeline_event(event_type: str, **data: Any) -> None:
    """Push a pipeline event if a consumer queue is active.

    Safe to call from anywhere — if no queue is set (e.g. non-SSE
    request path) the event is silently dropped.
    """
    q = pipeline_events_var.get()
    if q is not None:
        await q.put({
            "type": event_type,
            "ts": time.time(),
            **data,
        })


async def emit_pipeline_done(final_data: dict[str, Any] | None = None) -> None:
    """Signal that the pipeline is complete."""
    q = pipeline_events_var.get()
    if q is not None:
        await q.put({
            "type": "done",
            "ts": time.time(),
            **(final_data or {}),
        })
