"""Local (in-memory) tool implementations.

These tools operate on application repositories directly — no external
HTTP calls needed. They provide the same BaseTool interface as HTTP
and mock tools so they can be registered in the ToolRegistry.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import structlog

from medai.domain.entities import (
    HistoryRecord,
    HistorySearchOutput,
    TimelineEvent,
    ToolName,
)
from medai.domain.interfaces import BaseTool, BaseTimelineRepository

logger = structlog.get_logger()


class LocalHistorySearchTool(BaseTool):
    """Search patient history from the in-memory timeline repository.

    Unlike HttpHistorySearchTool (which calls an external RAG endpoint),
    this implementation reads directly from our TimelineRepository.
    For the hackathon prototype this gives instant, reliable results.
    In production this would be swapped for a vector-search backed tool.
    """

    def __init__(self, timeline_repo: BaseTimelineRepository) -> None:
        self._repo = timeline_repo

    @property
    def name(self) -> ToolName:
        return ToolName.HISTORY_SEARCH

    @property
    def description(self) -> str:
        return (
            "Search a patient's medical history for relevant prior records, "
            "imaging studies, lab results, and encounters. Returns the most "
            "clinically relevant records with similarity scores."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "patient_id": {
                    "type": "string",
                    "description": "Patient identifier to search history for",
                },
                "query": {
                    "type": "string",
                    "description": "Clinical query to search (e.g., 'prior chest imaging')",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of records to return",
                    "default": 10,
                },
            },
            "required": ["patient_id", "query"],
        }

    async def execute(self, **kwargs: Any) -> HistorySearchOutput:
        patient_id: str = kwargs.get("patient_id", "")
        query: str = kwargs.get("query", "")
        max_results: int = kwargs.get("max_results", 10)

        logger.info(
            "local_history_search",
            patient_id=patient_id,
            query=query[:80],
        )

        # Get all timeline events for this patient
        events: list[TimelineEvent] = await self._repo.get_for_patient(patient_id)

        if not events:
            logger.info("no_history_found", patient_id=patient_id)
            return HistorySearchOutput(
                patient_id=patient_id,
                relevant_records=[],
                timeline_context=(
                    f"No prior medical records found for patient {patient_id}. "
                    "This is a new patient or records have not been migrated."
                ),
            )

        # Convert timeline events to HistoryRecords
        # Simple keyword-based relevance scoring (production would use embeddings)
        query_lower = query.lower()
        query_words = set(query_lower.split())

        scored_records: list[tuple[float, HistoryRecord]] = []
        for event in events[:max_results]:
            # Simple term-overlap similarity
            event_text = f"{event.summary} {event.event_type.value}".lower()
            event_words = set(event_text.split())
            overlap = len(query_words & event_words)
            score = min(0.95, 0.3 + (overlap * 0.15))  # base 0.3 + boost per match

            record = HistoryRecord(
                date=event.date,
                record_type=event.event_type.value,
                summary=event.summary,
                similarity_score=score,
                clinical_relevance=(
                    f"Prior {event.event_type.value} record from "
                    f"{event.date.strftime('%Y-%m-%d')}: {event.summary[:120]}"
                ),
            )
            scored_records.append((score, record))

        # Sort by score descending, take top N
        scored_records.sort(key=lambda x: x[0], reverse=True)
        records = [r for _, r in scored_records[:max_results]]

        # Build timeline narrative
        event_summaries = [
            f"- [{e.date.strftime('%Y-%m-%d')}] {e.event_type.value}: {e.summary}"
            for e in events[:5]
        ]
        timeline_context = (
            f"Patient has {len(events)} prior timeline entries. "
            f"Most recent records:\n" + "\n".join(event_summaries)
        )

        logger.info(
            "history_search_complete",
            patient_id=patient_id,
            records_found=len(records),
        )

        return HistorySearchOutput(
            patient_id=patient_id,
            relevant_records=records,
            timeline_context=timeline_context,
        )
