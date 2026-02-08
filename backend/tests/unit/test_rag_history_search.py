"""Dedicated RAG tests — validates TF-IDF history search against seed data.

Ensures the LocalHistorySearchTool:
1. Returns relevant records for medical queries
2. Ranks results by TF-IDF cosine similarity (not random)
3. Handles empty patient history gracefully
4. Returns meaningful timeline_context narrative
5. Searches across different clinical domains (respiratory, renal, dermatology)
"""

from __future__ import annotations

import pytest

from medai.domain.entities import HistorySearchOutput
from medai.repositories.memory import InMemoryTimelineRepository
from medai.repositories.seed import create_seed_timeline_events
from medai.tools.local import LocalHistorySearchTool


@pytest.fixture
def seeded_repo() -> InMemoryTimelineRepository:
    """Timeline repo pre-loaded with all 23 seed events."""
    repo = InMemoryTimelineRepository()
    repo.seed(create_seed_timeline_events())
    return repo


@pytest.fixture
def rag_tool(seeded_repo: InMemoryTimelineRepository) -> LocalHistorySearchTool:
    return LocalHistorySearchTool(seeded_repo)


# ═══════════════════════════════════════════════════════
#  Maria Ivanova (PT-DEMO0001) — Respiratory Case
# ═══════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_rag_pneumonia_query_returns_relevant_records(rag_tool: LocalHistorySearchTool):
    """Querying 'pneumonia consolidation' should surface Maria's chest imaging and acute visit."""
    result: HistorySearchOutput = await rag_tool.execute(
        patient_id="PT-DEMO0001",
        query="pneumonia consolidation chest x-ray",
    )
    assert len(result.relevant_records) > 0
    # The current chest X-ray showing RLL consolidation should rank high
    summaries = [r.summary for r in result.relevant_records]
    found_cxr = any("consolidation" in s.lower() for s in summaries)
    assert found_cxr, f"Expected consolidation-related record in top results, got: {summaries[:3]}"


@pytest.mark.asyncio
async def test_rag_copd_query_ranks_pft_highly(rag_tool: LocalHistorySearchTool):
    """Querying 'COPD pulmonary function' should rank PFT and emphysema records highest."""
    result: HistorySearchOutput = await rag_tool.execute(
        patient_id="PT-DEMO0001",
        query="COPD pulmonary function test FEV1",
    )
    assert len(result.relevant_records) >= 3
    # Top result should be about PFT or emphysema
    top_summary = result.relevant_records[0].summary.lower()
    assert any(
        kw in top_summary for kw in ["fev1", "copd", "emphysema", "pulmonary function"]
    ), f"Top result should be PFT/COPD-related, got: {top_summary[:120]}"


@pytest.mark.asyncio
async def test_rag_similarity_scores_are_ordered(rag_tool: LocalHistorySearchTool):
    """Records should be sorted by descending similarity score."""
    result: HistorySearchOutput = await rag_tool.execute(
        patient_id="PT-DEMO0001",
        query="chest imaging findings",
    )
    scores = [r.similarity_score for r in result.relevant_records]
    assert scores == sorted(scores, reverse=True), f"Scores not sorted descending: {scores}"


@pytest.mark.asyncio
async def test_rag_timeline_context_narrative(rag_tool: LocalHistorySearchTool):
    """timeline_context should contain a structured narrative with relevance scores."""
    result: HistorySearchOutput = await rag_tool.execute(
        patient_id="PT-DEMO0001",
        query="prior chest imaging, pneumonia, respiratory infections",
    )
    assert "9 prior timeline entries" in result.timeline_context
    assert "TF-IDF similarity" in result.timeline_context
    assert "relevance:" in result.timeline_context


@pytest.mark.asyncio
async def test_rag_max_results_respected(rag_tool: LocalHistorySearchTool):
    """max_results parameter should limit the number of returned records."""
    result: HistorySearchOutput = await rag_tool.execute(
        patient_id="PT-DEMO0001",
        query="any medical history",
        max_results=3,
    )
    assert len(result.relevant_records) == 3


# ═══════════════════════════════════════════════════════
#  Oleksandr Petrenko (PT-DEMO0002) — Diabetes + Renal
# ═══════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_rag_diabetes_query_finds_hba1c(rag_tool: LocalHistorySearchTool):
    """Querying diabetes terms should surface HbA1c lab results."""
    result: HistorySearchOutput = await rag_tool.execute(
        patient_id="PT-DEMO0002",
        query="diabetes HbA1c glycemic control",
    )
    assert len(result.relevant_records) > 0
    summaries = " ".join(r.summary for r in result.relevant_records[:3])
    assert "hba1c" in summaries.lower(), f"Expected HbA1c in top 3, got: {summaries[:200]}"


@pytest.mark.asyncio
async def test_rag_nephropathy_query_finds_renal(rag_tool: LocalHistorySearchTool):
    """Querying renal terms should surface kidney function labs."""
    result: HistorySearchOutput = await rag_tool.execute(
        patient_id="PT-DEMO0002",
        query="nephropathy eGFR creatinine microalbuminuria",
    )
    assert len(result.relevant_records) > 0
    summaries = " ".join(r.summary for r in result.relevant_records[:3])
    assert any(
        kw in summaries.lower() for kw in ["egfr", "creatinine", "nephropathy", "acr"]
    ), f"Expected renal-related terms in top results, got: {summaries[:200]}"


# ═══════════════════════════════════════════════════════
#  Natalia Kovalenko (PT-DEMO0003) — Dermatology
# ═══════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_rag_melanoma_query_finds_biopsy(rag_tool: LocalHistorySearchTool):
    """Querying melanoma should surface biopsy and staging records."""
    result: HistorySearchOutput = await rag_tool.execute(
        patient_id="PT-DEMO0003",
        query="melanoma biopsy Breslow thickness staging",
    )
    assert len(result.relevant_records) > 0
    summaries = " ".join(r.summary for r in result.relevant_records[:3])
    assert any(
        kw in summaries.lower() for kw in ["melanoma", "breslow", "biopsy", "staging"]
    ), f"Expected melanoma-related terms, got: {summaries[:200]}"


# ═══════════════════════════════════════════════════════
#  Edge Cases
# ═══════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_rag_unknown_patient_returns_empty(rag_tool: LocalHistorySearchTool):
    """Non-existent patient should return empty records with a helpful message."""
    result: HistorySearchOutput = await rag_tool.execute(
        patient_id="PT-UNKNOWN-999",
        query="any query",
    )
    assert result.relevant_records == []
    assert "No prior medical records" in result.timeline_context
    assert "PT-UNKNOWN-999" in result.timeline_context


@pytest.mark.asyncio
async def test_rag_cross_patient_isolation(rag_tool: LocalHistorySearchTool):
    """Querying patient A should never return patient B's records."""
    result: HistorySearchOutput = await rag_tool.execute(
        patient_id="PT-DEMO0001",
        query="melanoma biopsy Breslow",
    )
    # Maria has no melanoma records — should still get results (respiratory),
    # but none should mention melanoma/Breslow
    for r in result.relevant_records:
        assert "melanoma" not in r.summary.lower(), (
            f"Cross-contamination: Maria's results contain Natalia's melanoma record: {r.summary}"
        )


@pytest.mark.asyncio
async def test_rag_clinical_relevance_field_populated(rag_tool: LocalHistorySearchTool):
    """Each record should have a formatted clinical_relevance string."""
    result: HistorySearchOutput = await rag_tool.execute(
        patient_id="PT-DEMO0002",
        query="diabetes labs",
    )
    for r in result.relevant_records:
        assert r.clinical_relevance.startswith("Prior "), f"Bad clinical_relevance: {r.clinical_relevance}"
        assert r.date is not None


@pytest.mark.asyncio
async def test_rag_top_score_higher_than_bottom(rag_tool: LocalHistorySearchTool):
    """For a specific query, the top match should have a meaningfully higher score than the bottom."""
    result: HistorySearchOutput = await rag_tool.execute(
        patient_id="PT-DEMO0001",
        query="pneumonia consolidation right lower lobe",
    )
    if len(result.relevant_records) >= 3:
        top_score = result.relevant_records[0].similarity_score
        bottom_score = result.relevant_records[-1].similarity_score
        assert top_score > bottom_score, (
            f"TF-IDF should differentiate relevant from irrelevant: "
            f"top={top_score}, bottom={bottom_score}"
        )
