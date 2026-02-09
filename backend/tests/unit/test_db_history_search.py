"""Tests for DbHistorySearchTool — validates DB-backed patient history retrieval.

Ensures the DbHistorySearchTool:
1. Retrieves timeline events from the database
2. Retrieves and summarises prior AI reports
3. Ranks results by TF-IDF cosine similarity
4. Handles patients with no history gracefully
5. Produces enriched timeline_context that includes prior report summaries
6. Works with the async session factory pattern (no Depends() required)
"""

from __future__ import annotations

import pytest
from datetime import date, datetime
from typing import Any, AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from medai.domain.entities import (
    ApprovalStatus,
    ConfidenceMethod,
    Finding,
    FinalReport,
    Gender,
    HistorySearchOutput,
    JudgmentResult,
    JudgeVerdict,
    Patient,
    Severity,
    TimelineEvent,
    TimelineEventType,
)
from medai.repositories.models import Base
from medai.repositories.sqlalchemy import (
    SqlAlchemyPatientRepository,
    SqlAlchemyReportRepository,
    SqlAlchemyTimelineRepository,
)
from medai.tools.local import DbHistorySearchTool


# ── Fixtures ──────────────────────────────────────────────


@pytest.fixture
async def db_session_factory() -> AsyncGenerator[async_sessionmaker[AsyncSession], None]:
    """Create an in-memory SQLite database with all tables for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield factory

    await engine.dispose()


@pytest.fixture
async def seeded_factory(
    db_session_factory: async_sessionmaker[AsyncSession],
) -> async_sessionmaker[AsyncSession]:
    """Seed the database with a patient, timeline events, and a prior report."""
    async with db_session_factory() as session:
        # Create patient
        patient_repo = SqlAlchemyPatientRepository(session)
        await patient_repo.create(
            Patient(
                id="PT-TEST001",
                name="Test Patient",
                date_of_birth=date(1965, 5, 20),
                gender=Gender.MALE,
            )
        )

        # Create timeline events (respiratory story)
        timeline_repo = SqlAlchemyTimelineRepository(session)
        await timeline_repo.add_event(
            TimelineEvent(
                id="TL-T001",
                patient_id="PT-TEST001",
                date=datetime(2025, 6, 1, 9, 0),
                event_type=TimelineEventType.ENCOUNTER,
                summary=(
                    "Initial consultation — chronic cough for 3 months, "
                    "productive with white sputum. 20-pack-year smoking history. "
                    "Auscultation: scattered wheezes bilaterally."
                ),
                source_type="encounter",
                metadata={"chief_complaint": "chronic cough"},
            )
        )
        await timeline_repo.add_event(
            TimelineEvent(
                id="TL-T002",
                patient_id="PT-TEST001",
                date=datetime(2025, 6, 1, 10, 0),
                event_type=TimelineEventType.LAB,
                summary="CBC normal. CRP 8 mg/L (mildly elevated). SpO2 96%.",
                source_type="lab",
                metadata={"crp": 8.0, "spo2": 96},
            )
        )
        await timeline_repo.add_event(
            TimelineEvent(
                id="TL-T003",
                patient_id="PT-TEST001",
                date=datetime(2025, 6, 2, 14, 0),
                event_type=TimelineEventType.IMAGING,
                summary=(
                    "Chest X-ray: Hyperinflated lungs, compatible with COPD. "
                    "No acute consolidation."
                ),
                source_type="imaging",
                metadata={"modality": "xray", "impression": "COPD"},
            )
        )
        await timeline_repo.add_event(
            TimelineEvent(
                id="TL-T004",
                patient_id="PT-TEST001",
                date=datetime(2025, 6, 3, 11, 0),
                event_type=TimelineEventType.PRESCRIPTION,
                summary="Started Tiotropium 18mcg daily. Smoking cessation counseling.",
                source_type="prescription",
                metadata={"drug": "Tiotropium", "dose": "18mcg"},
            )
        )
        await timeline_repo.add_event(
            TimelineEvent(
                id="TL-T005",
                patient_id="PT-TEST001",
                date=datetime(2025, 12, 10, 9, 0),
                event_type=TimelineEventType.ENCOUNTER,
                summary=(
                    "Follow-up: Patient reports persistent chronic cough despite "
                    "Tiotropium. Still smoking 10/day. SpO2 95%. "
                    "Added Fluticasone/Salmeterol 250/50 BID."
                ),
                source_type="encounter",
                metadata={"chief_complaint": "persistent cough"},
            )
        )

        # Create a prior AI report
        report_repo = SqlAlchemyReportRepository(session)
        await report_repo.save(
            FinalReport(
                id="RPT-TEST001",
                encounter_id="ENC-TEST001",
                patient_id="PT-TEST001",
                diagnosis="COPD GOLD Stage II with chronic bronchitis",
                confidence=0.82,
                confidence_method=ConfidenceMethod.MODEL_SELF_REPORTED,
                evidence_summary="Chronic cough, smoking history, imaging consistent with COPD",
                timeline_impact="Patient has progressive respiratory disease",
                plan=[
                    "Continue Tiotropium",
                    "Add ICS/LABA combination",
                    "Smoking cessation program",
                    "Follow-up PFT in 3 months",
                ],
                findings=[
                    Finding(
                        finding="Chronic obstructive pulmonary disease",
                        confidence=0.82,
                        explanation="20-pack-year history with hyperinflated lungs on CXR",
                        severity=Severity.MODERATE,
                    ),
                ],
                reasoning_trace=[],
                specialist_outputs={},
                judge_verdict=JudgmentResult(
                    verdict=JudgeVerdict.CONSENSUS,
                    confidence=0.80,
                    reasoning="Consistent findings across tools",
                    contradictions=[],
                    low_confidence_items=[],
                    missing_context=[],
                    requery_tools=[],
                ),
                approval_status=ApprovalStatus.APPROVED,
                doctor_notes="Confirmed COPD diagnosis. Patient educated.",
                created_at=datetime(2025, 6, 5, 12, 0),
            )
        )

        await session.commit()

    return db_session_factory


@pytest.fixture
def db_tool(seeded_factory: async_sessionmaker[AsyncSession]) -> DbHistorySearchTool:
    """DbHistorySearchTool backed by the seeded test database."""
    return DbHistorySearchTool(seeded_factory)


# ═══════════════════════════════════════════════════════════
#  Core retrieval tests
# ═══════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_db_tool_returns_relevant_records(db_tool: DbHistorySearchTool):
    """Querying 'chronic cough COPD' should return timeline records."""
    result: HistorySearchOutput = await db_tool.execute(
        patient_id="PT-TEST001",
        query="chronic cough COPD",
    )
    assert len(result.relevant_records) > 0
    summaries = " ".join(r.summary.lower() for r in result.relevant_records)
    assert "cough" in summaries or "copd" in summaries


@pytest.mark.asyncio
async def test_db_tool_includes_prior_reports_in_context(db_tool: DbHistorySearchTool):
    """timeline_context should mention prior AI reports."""
    result: HistorySearchOutput = await db_tool.execute(
        patient_id="PT-TEST001",
        query="respiratory diagnosis",
    )
    assert "PRIOR AI REPORT" in result.timeline_context
    assert "COPD GOLD Stage II" in result.timeline_context


@pytest.mark.asyncio
async def test_db_tool_includes_doctor_notes(db_tool: DbHistorySearchTool):
    """Prior report doctor notes should appear in context."""
    result: HistorySearchOutput = await db_tool.execute(
        patient_id="PT-TEST001",
        query="any query",
    )
    assert "Doctor notes:" in result.timeline_context
    assert "Confirmed COPD" in result.timeline_context


@pytest.mark.asyncio
async def test_db_tool_includes_plan_from_prior_reports(db_tool: DbHistorySearchTool):
    """Prior report plans should appear in context."""
    result: HistorySearchOutput = await db_tool.execute(
        patient_id="PT-TEST001",
        query="treatment plan",
    )
    assert "Tiotropium" in result.timeline_context
    assert "Smoking cessation" in result.timeline_context


@pytest.mark.asyncio
async def test_db_tool_records_sorted_by_similarity(db_tool: DbHistorySearchTool):
    """Records should be sorted descending by similarity score."""
    result: HistorySearchOutput = await db_tool.execute(
        patient_id="PT-TEST001",
        query="chest imaging findings",
    )
    scores = [r.similarity_score for r in result.relevant_records]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_db_tool_max_results_respected(db_tool: DbHistorySearchTool):
    """max_results parameter should limit the number of returned records."""
    result: HistorySearchOutput = await db_tool.execute(
        patient_id="PT-TEST001",
        query="any medical history",
        max_results=2,
    )
    assert len(result.relevant_records) <= 2


# ═══════════════════════════════════════════════════════════
#  Edge cases
# ═══════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_db_tool_unknown_patient_returns_empty(db_tool: DbHistorySearchTool):
    """Non-existent patient should return empty records with a helpful message."""
    result: HistorySearchOutput = await db_tool.execute(
        patient_id="PT-NONEXISTENT",
        query="anything",
    )
    assert result.relevant_records == []
    assert "No prior medical records" in result.timeline_context


@pytest.mark.asyncio
async def test_db_tool_tool_metadata(db_tool: DbHistorySearchTool):
    """Tool should expose correct name, description, and schema."""
    from medai.domain.entities import ToolName

    assert db_tool.name == ToolName.HISTORY_SEARCH
    assert "medical history" in db_tool.description.lower()
    assert "patient_id" in db_tool.input_schema["properties"]
    assert "query" in db_tool.input_schema["properties"]


@pytest.mark.asyncio
async def test_db_tool_claude_definition(db_tool: DbHistorySearchTool):
    """to_claude_tool_definition should produce a valid Claude tool schema."""
    defn = db_tool.to_claude_tool_definition()
    assert defn["name"] == "history_search"
    assert "input_schema" in defn
    assert defn.get("strict") is True


# ═══════════════════════════════════════════════════════════
#  Report context formatting
# ═══════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_db_tool_report_context_shows_approval_status(db_tool: DbHistorySearchTool):
    """The report summary should show the approval status."""
    result: HistorySearchOutput = await db_tool.execute(
        patient_id="PT-TEST001",
        query="any",
    )
    assert "approved" in result.timeline_context.lower()


@pytest.mark.asyncio
async def test_db_tool_report_context_shows_findings(db_tool: DbHistorySearchTool):
    """The report summary should include key findings."""
    result: HistorySearchOutput = await db_tool.execute(
        patient_id="PT-TEST001",
        query="findings",
    )
    assert "Chronic obstructive pulmonary disease" in result.timeline_context
