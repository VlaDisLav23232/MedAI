"""Tests for SQLAlchemy repositories — real async DB operations.

Uses aiosqlite in-memory database for fast, isolated testing.
Each test gets a fresh database with tables created from scratch.
"""

from __future__ import annotations

import os
from datetime import date, datetime

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Ensure test env vars are set before importing app code
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-key-not-real")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from medai.domain.entities import (
    ApprovalStatus,
    ConfidenceMethod,
    Finding,
    FinalReport,
    Gender,
    JudgmentResult,
    Patient,
    PipelineMetrics,
    Severity,
    TimelineEvent,
    TimelineEventType,
    User,
    UserRole,
)
from medai.repositories.models import Base
from medai.repositories.sqlalchemy import (
    SqlAlchemyPatientRepository,
    SqlAlchemyReportRepository,
    SqlAlchemyTimelineRepository,
    SqlAlchemyUserRepository,
)


@pytest_asyncio.fixture
async def engine():
    """Create a fresh in-memory SQLite engine for each test."""
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine):
    """Provide a per-test async session."""
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        yield sess
        await sess.rollback()


# ═══════════════════════════════════════════════════════════════
#  User Repository Tests
# ═══════════════════════════════════════════════════════════════


@pytest.mark.unit
@pytest.mark.asyncio
async def test_user_create_and_get_by_id(session):
    repo = SqlAlchemyUserRepository(session)
    user = User(
        email="test@example.com",
        hashed_password="hashed123",
        name="Test User",
        role=UserRole.DOCTOR,
    )
    created = await repo.create(user)
    assert created.id == user.id
    assert created.email == "test@example.com"
    assert created.role == UserRole.DOCTOR

    fetched = await repo.get_by_id(user.id)
    assert fetched is not None
    assert fetched.email == "test@example.com"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_user_get_by_email(session):
    repo = SqlAlchemyUserRepository(session)
    user = User(
        email="doctor@hospital.com",
        hashed_password="hash",
        name="Dr. Test",
        role=UserRole.DOCTOR,
    )
    await repo.create(user)
    await session.commit()

    found = await repo.get_by_email("doctor@hospital.com")
    assert found is not None
    assert found.name == "Dr. Test"

    not_found = await repo.get_by_email("nonexistent@example.com")
    assert not_found is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_user_list_all(session):
    repo = SqlAlchemyUserRepository(session)
    await repo.create(User(email="a@test.com", hashed_password="h", name="A", role=UserRole.DOCTOR))
    await repo.create(User(email="b@test.com", hashed_password="h", name="B", role=UserRole.ADMIN))
    await session.commit()

    users = await repo.list_all()
    assert len(users) == 2
    emails = {u.email for u in users}
    assert emails == {"a@test.com", "b@test.com"}


# ═══════════════════════════════════════════════════════════════
#  Patient Repository Tests
# ═══════════════════════════════════════════════════════════════


@pytest.mark.unit
@pytest.mark.asyncio
async def test_patient_create_and_get(session):
    repo = SqlAlchemyPatientRepository(session)
    patient = Patient(
        id="PT-TEST0001",
        name="John Doe",
        date_of_birth=date(1990, 5, 15),
        gender=Gender.MALE,
        medical_record_number="MRN-001",
    )
    created = await repo.create(patient)
    assert created.id == "PT-TEST0001"
    assert created.name == "John Doe"

    fetched = await repo.get("PT-TEST0001")
    assert fetched is not None
    assert fetched.date_of_birth == date(1990, 5, 15)
    assert fetched.gender == Gender.MALE


@pytest.mark.unit
@pytest.mark.asyncio
async def test_patient_list_all(session):
    repo = SqlAlchemyPatientRepository(session)
    await repo.create(Patient(id="PT-A", name="A", date_of_birth=date(2000, 1, 1)))
    await repo.create(Patient(id="PT-B", name="B", date_of_birth=date(2001, 1, 1)))
    await session.commit()

    patients = await repo.list_all()
    assert len(patients) == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_patient_not_found(session):
    repo = SqlAlchemyPatientRepository(session)
    result = await repo.get("PT-DOESNOTEXIST")
    assert result is None


# ═══════════════════════════════════════════════════════════════
#  Timeline Repository Tests
# ═══════════════════════════════════════════════════════════════


@pytest.mark.unit
@pytest.mark.asyncio
async def test_timeline_add_and_get(session):
    repo = SqlAlchemyTimelineRepository(session)
    event = TimelineEvent(
        id="TL-TEST0001",
        patient_id="PT-TEST0001",
        date=datetime(2025, 6, 15, 10, 0),
        event_type=TimelineEventType.LAB,
        summary="Blood work results",
        metadata={"wbc": "7.2", "crp": "12"},
    )
    created = await repo.add_event(event)
    assert created.id == "TL-TEST0001"

    events = await repo.get_for_patient("PT-TEST0001")
    assert len(events) == 1
    assert events[0].summary == "Blood work results"
    assert events[0].metadata["wbc"] == "7.2"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_timeline_sorted_desc(session):
    repo = SqlAlchemyTimelineRepository(session)
    await repo.add_event(TimelineEvent(
        id="TL-OLD", patient_id="PT-1",
        date=datetime(2025, 1, 1), event_type=TimelineEventType.LAB,
        summary="Old event",
    ))
    await repo.add_event(TimelineEvent(
        id="TL-NEW", patient_id="PT-1",
        date=datetime(2025, 12, 1), event_type=TimelineEventType.IMAGING,
        summary="New event",
    ))
    await session.commit()

    events = await repo.get_for_patient("PT-1")
    assert len(events) == 2
    assert events[0].id == "TL-NEW"  # newest first
    assert events[1].id == "TL-OLD"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_timeline_empty_patient(session):
    repo = SqlAlchemyTimelineRepository(session)
    events = await repo.get_for_patient("PT-NONEXISTENT")
    assert events == []


# ═══════════════════════════════════════════════════════════════
#  Report Repository Tests
# ═══════════════════════════════════════════════════════════════


def _make_report(report_id: str = "RPT-TEST0001", patient_id: str = "PT-TEST0001") -> FinalReport:
    """Helper to create a test FinalReport with realistic data."""
    return FinalReport(
        id=report_id,
        encounter_id="ENC-TEST0001",
        patient_id=patient_id,
        diagnosis="Community-acquired pneumonia",
        confidence=0.87,
        confidence_method=ConfidenceMethod.JUDGE_ASSESSMENT,
        evidence_summary="Chest X-ray shows bilateral infiltrates",
        timeline_impact="First pneumonia episode, no prior respiratory issues",
        plan=["Start antibiotics", "Follow-up X-ray in 48h"],
        findings=[
            Finding(
                finding="Bilateral infiltrates",
                confidence=0.9,
                explanation="Consistent with pneumonia",
                severity=Severity.MODERATE,
            ),
        ],
        reasoning_trace=[{"step": "Analyzed X-ray", "conclusion": "Pneumonia likely"}],
        specialist_outputs={"image_analysis": {"summary": "Infiltrates detected"}},
        judge_verdict=JudgmentResult(
            verdict="consensus",
            confidence=0.85,
            reasoning="Tools agree on pneumonia diagnosis",
        ),
        approval_status=ApprovalStatus.PENDING,
        pipeline_metrics=PipelineMetrics(
            tools_s=3.2,
            judge_s=1.1,
            report_s=0.5,
            total_s=4.8,
        ),
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_report_save_and_get(session):
    repo = SqlAlchemyReportRepository(session)
    report = _make_report()
    saved = await repo.save(report)
    assert saved.id == "RPT-TEST0001"
    assert saved.diagnosis == "Community-acquired pneumonia"

    fetched = await repo.get("RPT-TEST0001")
    assert fetched is not None
    assert fetched.confidence == 0.87
    assert fetched.confidence_method == ConfidenceMethod.JUDGE_ASSESSMENT
    assert len(fetched.findings) == 1
    assert fetched.findings[0].finding == "Bilateral infiltrates"
    assert fetched.judge_verdict is not None
    assert fetched.judge_verdict.verdict == "consensus"
    assert fetched.pipeline_metrics is not None
    assert fetched.pipeline_metrics.total_s == 4.8
    assert fetched.plan == ["Start antibiotics", "Follow-up X-ray in 48h"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_report_update_approval(session):
    repo = SqlAlchemyReportRepository(session)
    await repo.save(_make_report())
    await session.commit()

    updated = await repo.update_approval(
        "RPT-TEST0001", "approved", doctor_notes="Looks correct"
    )
    assert updated is not None
    assert updated.approval_status == ApprovalStatus.APPROVED
    assert updated.doctor_notes == "Looks correct"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_report_list_for_patient(session):
    repo = SqlAlchemyReportRepository(session)
    await repo.save(_make_report("RPT-A", "PT-1"))
    await repo.save(_make_report("RPT-B", "PT-1"))
    await repo.save(_make_report("RPT-C", "PT-2"))
    await session.commit()

    reports = await repo.list_for_patient("PT-1")
    assert len(reports) == 2
    ids = {r.id for r in reports}
    assert ids == {"RPT-A", "RPT-B"}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_report_not_found(session):
    repo = SqlAlchemyReportRepository(session)
    result = await repo.get("RPT-DOESNOTEXIST")
    assert result is None
