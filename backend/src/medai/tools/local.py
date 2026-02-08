"""Local (in-memory) tool implementations with vector-based retrieval.

These tools operate on application repositories directly — no external
HTTP calls needed. They provide the same BaseTool interface as HTTP
and mock tools so they can be registered in the ToolRegistry.

History search uses TF-IDF vectorization with cosine similarity
for semantic-aware retrieval over the patient timeline.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import structlog
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from medai.domain.entities import (
    HistoryRecord,
    HistorySearchOutput,
    TimelineEvent,
    ToolName,
)
from medai.domain.interfaces import BaseTool, BaseTimelineRepository

logger = structlog.get_logger()


class LocalHistorySearchTool(BaseTool):
    """Search patient history using TF-IDF vector similarity.

    Unlike HttpHistorySearchTool (which calls an external RAG endpoint),
    this implementation reads directly from our TimelineRepository and
    uses TF-IDF + cosine similarity for semantic-aware retrieval.

    Architecture note: TF-IDF is a lightweight baseline. In production,
    swap for dense embeddings (MedCPT, PubMedBERT, or sentence-transformers)
    with FAISS/ChromaDB for sub-millisecond retrieval at scale.
    """

    def __init__(self, timeline_repo: BaseTimelineRepository) -> None:
        self._repo = timeline_repo
        self._vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),  # unigrams + bigrams for medical terms
            max_features=5000,
            sublinear_tf=True,  # logarithmic TF scaling
        )

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
            "additionalProperties": False,
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

        # ── TF-IDF Vector Similarity Retrieval ────────────
        # Build document corpus from timeline events
        event_texts = [
            f"{event.event_type.value} {event.summary} "
            f"{' '.join(str(v) for v in event.metadata.values())}"
            for event in events
        ]

        # Fit TF-IDF on corpus + query together for shared vocabulary
        all_texts = event_texts + [query]
        try:
            tfidf_matrix = self._vectorizer.fit_transform(all_texts)

            # Query is the last vector; events are all others
            query_vector = tfidf_matrix[-1:]
            event_vectors = tfidf_matrix[:-1]

            # Compute cosine similarity between query and all events
            similarities = cosine_similarity(query_vector, event_vectors).flatten()
        except ValueError:
            # Fallback if vectorization fails (empty vocab, etc.)
            logger.warning("tfidf_fallback", reason="vectorization failed")
            similarities = [0.3] * len(events)

        # Build scored records
        scored_records: list[tuple[float, HistoryRecord, TimelineEvent]] = []
        for i, (event, sim_score) in enumerate(zip(events, similarities)):
            # Normalize to 0-1 range with a base relevance boost
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

        # Sort by similarity descending, take top N
        scored_records.sort(key=lambda x: x[0], reverse=True)
        records = [r for _, r, _ in scored_records[:max_results]]

        # Build timeline narrative from most relevant events
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

        logger.info(
            "history_search_complete",
            patient_id=patient_id,
            records_found=len(records),
            top_similarity=round(scored_records[0][0], 3) if scored_records else 0,
            method="tfidf_cosine",
        )

        return HistorySearchOutput(
            patient_id=patient_id,
            relevant_records=records,
            timeline_context=timeline_context,
        )
