"""Local (in-memory and DB-backed) tool implementations with vector-based retrieval.

These tools operate on application repositories directly — no external
HTTP calls needed. They provide the same BaseTool interface as HTTP
and mock tools so they can be registered in the ToolRegistry.

History search uses TF-IDF vectorization with cosine similarity
for semantic-aware retrieval over the patient timeline.

Two implementations are provided:

- ``LocalHistorySearchTool``: reads from an injected
  ``BaseTimelineRepository`` (test-friendly, works with
  ``InMemoryTimelineRepository``).
- ``DbHistorySearchTool``: creates its own async DB session per
  ``execute()`` call so it can live inside the singleton ToolRegistry
  while still querying the real database for timeline **and** prior
  AI report data.
"""

from __future__ import annotations

from typing import Any

import structlog
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from medai.domain.entities import (
    FinalReport,
    HistoryRecord,
    HistorySearchOutput,
    TimelineEvent,
    ToolName,
)
from medai.domain.interfaces import BaseTool, BaseTimelineRepository

logger = structlog.get_logger()


# ═══════════════════════════════════════════════════════════
#  Shared TF-IDF retrieval helpers
# ═══════════════════════════════════════════════════════════


def _build_tfidf_vectorizer() -> TfidfVectorizer:
    """Create a TF-IDF vectorizer tuned for medical text retrieval."""
    return TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),  # unigrams + bigrams for medical terms
        max_features=5000,
        sublinear_tf=True,  # logarithmic TF scaling
    )


def _rank_events_by_similarity(
    events: list[TimelineEvent],
    query: str,
    max_results: int,
) -> tuple[list[HistoryRecord], str]:
    """Rank timeline events against *query* using TF-IDF cosine similarity.

    Returns:
        (ranked_records, timeline_context_narrative)
    """
    vectorizer = _build_tfidf_vectorizer()

    event_texts = [
        f"{event.event_type.value} {event.summary} "
        f"{' '.join(str(v) for v in event.metadata.values())}"
        for event in events
    ]

    all_texts = event_texts + [query]
    try:
        tfidf_matrix = vectorizer.fit_transform(all_texts)
        query_vector = tfidf_matrix[-1:]
        event_vectors = tfidf_matrix[:-1]
        similarities = cosine_similarity(query_vector, event_vectors).flatten()
    except ValueError:
        logger.warning("tfidf_fallback", reason="vectorization failed")
        similarities = [0.3] * len(events)

    scored_records: list[tuple[float, HistoryRecord, TimelineEvent]] = []
    for event, sim_score in zip(events, similarities):
        score = min(0.99, float(sim_score) * 0.7 + 0.3)
        record = HistoryRecord(
            date=event.date,
            record_type=event.event_type.value,
            summary=event.summary,
            similarity_score=round(score, 3),
            clinical_relevance=(
                f"Prior {event.event_type.value} from "
                f"{event.date.strftime('%Y-%m-%d')}: {event.summary[:120]}"
            ),
        )
        scored_records.append((score, record, event))

    scored_records.sort(key=lambda x: x[0], reverse=True)
    records = [r for _, r, _ in scored_records[:max_results]]

    top_events = scored_records[:5]
    event_summaries = [
        f"- [{ev.date.strftime('%Y-%m-%d')}] {ev.event_type.value}: "
        f"{ev.summary[:150]} (relevance: {score:.2f})"
        for score, _, ev in top_events
    ]
    timeline_context = (
        f"Patient has {len(events)} prior timeline entries. "
        f"Top matches by TF-IDF similarity to query:\n"
        + "\n".join(event_summaries)
    )

    return records, timeline_context


def _build_report_context(reports: list[FinalReport]) -> str:
    """Summarise prior AI reports into a concise clinical context string.

    Extracts diagnoses, key findings, treatment plans, and approval
    status so the orchestrator / text-reasoning agent can integrate
    longitudinal AI-generated insights when forming its current verdict.
    """
    if not reports:
        return ""

    lines: list[str] = [
        f"=== {len(reports)} PRIOR AI REPORT(S) ===",
    ]
    for rpt in sorted(reports, key=lambda r: r.created_at, reverse=True):
        status = rpt.approval_status.value
        date_str = rpt.created_at.strftime("%Y-%m-%d %H:%M")
        findings_summary = "; ".join(
            f"{f.finding} ({f.severity.value}, conf={f.confidence:.0%})"
            for f in (rpt.findings or [])[:5]
        )
        plan_summary = "; ".join(rpt.plan[:5]) if rpt.plan else "none"

        lines.append(
            f"[{date_str}] Dx: {rpt.diagnosis} | Confidence: {rpt.confidence:.0%} "
            f"| Status: {status}"
        )
        if findings_summary:
            lines.append(f"  Findings: {findings_summary}")
        if plan_summary:
            lines.append(f"  Plan: {plan_summary}")
        if rpt.doctor_notes:
            lines.append(f"  Doctor notes: {rpt.doctor_notes}")
    return "\n".join(lines)


def _empty_history_output(patient_id: str) -> HistorySearchOutput:
    """Return a well-formed empty result for patients with no history."""
    return HistorySearchOutput(
        patient_id=patient_id,
        relevant_records=[],
        timeline_context=(
            f"No prior medical records found for patient {patient_id}. "
            "This is a new patient or records have not been migrated."
        ),
    )


# ── Shared tool metadata ──────────────────────────────────

_HISTORY_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "patient_id": {
            "type": "string",
            "description": "Patient identifier to search history for",
        },
        "query": {
            "type": "string",
            "description": (
                "Clinical query describing what to look for in the "
                "patient's history (e.g., 'prior chest imaging', "
                "'chronic cough history', 'diabetes medication changes')"
            ),
        },
        "max_results": {
            "type": "integer",
            "description": "Maximum number of timeline records to return",
            "default": 10,
        },
    },
    "required": ["patient_id", "query"],
    "additionalProperties": False,
}

_HISTORY_DESCRIPTION = (
    "Search a patient's medical history and prior AI reports for "
    "clinically relevant context. Returns ranked historical records "
    "(encounters, imaging, labs, procedures, prescriptions) plus "
    "summaries of previous AI-generated diagnoses and treatment plans. "
    "Use this to understand chronic conditions, prior treatments, and "
    "longitudinal trends that may influence the current assessment."
)


# ═══════════════════════════════════════════════════════════
#  LocalHistorySearchTool (injected repo — for tests)
# ═══════════════════════════════════════════════════════════


class LocalHistorySearchTool(BaseTool):
    """Search patient history using TF-IDF vector similarity.

    Reads directly from an injected ``BaseTimelineRepository``.
    Best used with ``InMemoryTimelineRepository`` in unit tests
    or for lightweight development.

    Architecture note: TF-IDF is a lightweight baseline. In production,
    swap for dense embeddings (MedCPT, PubMedBERT, or sentence-transformers)
    with FAISS/ChromaDB for sub-millisecond retrieval at scale.
    """

    def __init__(self, timeline_repo: BaseTimelineRepository) -> None:
        self._repo = timeline_repo

    @property
    def name(self) -> ToolName:
        return ToolName.HISTORY_SEARCH

    @property
    def description(self) -> str:
        return _HISTORY_DESCRIPTION

    @property
    def input_schema(self) -> dict[str, Any]:
        return _HISTORY_INPUT_SCHEMA

    async def execute(self, **kwargs: Any) -> HistorySearchOutput:
        patient_id: str = kwargs.get("patient_id", "")
        query: str = kwargs.get("query", "")
        max_results: int = kwargs.get("max_results", 10)

        logger.info(
            "local_history_search",
            patient_id=patient_id,
            query=query[:80],
        )

        events: list[TimelineEvent] = await self._repo.get_for_patient(patient_id)

        if not events:
            logger.info("no_history_found", patient_id=patient_id)
            return _empty_history_output(patient_id)

        records, timeline_context = _rank_events_by_similarity(events, query, max_results)

        logger.info(
            "history_search_complete",
            patient_id=patient_id,
            records_found=len(records),
            top_similarity=records[0].similarity_score if records else 0,
            method="tfidf_cosine",
        )

        return HistorySearchOutput(
            patient_id=patient_id,
            relevant_records=records,
            timeline_context=timeline_context,
        )


# ═══════════════════════════════════════════════════════════
#  DbHistorySearchTool (session-factory — for production)
# ═══════════════════════════════════════════════════════════


class DbHistorySearchTool(BaseTool):
    """Search patient history **and** prior AI reports from the database.

    Unlike ``LocalHistorySearchTool`` this tool is designed to live
    inside the singleton ``ToolRegistry``.  It accepts a SQLAlchemy
    ``async_sessionmaker`` and opens a short-lived read-only session
    for each ``execute()`` call, so it works correctly with per-request
    isolation without requiring FastAPI ``Depends()``.

    Retrieval pipeline:

    1. Fetch all timeline events for the patient from the DB.
    2. Fetch all prior AI reports for the patient from the DB.
    3. Rank timeline events against the clinical query via TF-IDF.
    4. Append a concise summary of prior reports (diagnoses, findings,
       plans, doctor notes) to the ``timeline_context``.

    The enriched ``timeline_context`` is what the orchestrator feeds
    back into the text-reasoning tool, enabling the agent to adjust
    its clinical assessment based on the patient's longitudinal record
    (e.g. chronic conditions, previously prescribed medications,
    recurring symptoms).
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    @property
    def name(self) -> ToolName:
        return ToolName.HISTORY_SEARCH

    @property
    def description(self) -> str:
        return _HISTORY_DESCRIPTION

    @property
    def input_schema(self) -> dict[str, Any]:
        return _HISTORY_INPUT_SCHEMA

    async def execute(self, **kwargs: Any) -> HistorySearchOutput:
        """Query the database for timeline events and prior reports."""
        patient_id: str = kwargs.get("patient_id", "")
        query: str = kwargs.get("query", "")
        max_results: int = kwargs.get("max_results", 10)

        logger.info(
            "db_history_search_start",
            patient_id=patient_id,
            query=query[:80],
        )

        # Import repo implementations here to avoid circular imports
        # at module level (repositories → entities → … → tools).
        from medai.repositories.sqlalchemy import (
            SqlAlchemyReportRepository,
            SqlAlchemyTimelineRepository,
        )

        async with self._session_factory() as session:
            timeline_repo = SqlAlchemyTimelineRepository(session)
            report_repo = SqlAlchemyReportRepository(session)

            events: list[TimelineEvent] = await timeline_repo.get_for_patient(patient_id)
            reports: list[FinalReport] = await report_repo.list_for_patient(patient_id)

        if not events and not reports:
            logger.info("no_history_found", patient_id=patient_id)
            return _empty_history_output(patient_id)

        # ── Rank timeline events via TF-IDF ────────────────
        if events:
            records, timeline_context = _rank_events_by_similarity(events, query, max_results)
        else:
            records = []
            timeline_context = "No timeline events found for this patient."

        # ── Append prior report summaries ──────────────────
        report_context = _build_report_context(reports)
        if report_context:
            timeline_context = f"{timeline_context}\n\n{report_context}"

        logger.info(
            "db_history_search_complete",
            patient_id=patient_id,
            timeline_events=len(events),
            prior_reports=len(reports),
            records_returned=len(records),
            top_similarity=records[0].similarity_score if records else 0,
            method="tfidf_cosine",
        )

        return HistorySearchOutput(
            patient_id=patient_id,
            relevant_records=records,
            timeline_context=timeline_context,
        )
