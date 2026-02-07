"""Unit tests for in-memory repository implementations."""

from __future__ import annotations

from datetime import date, datetime

import pytest

from medai.domain.entities import (
    ApprovalStatus,
    FinalReport,
    Finding,
    Gender,
    JudgmentResult,
    JudgeVerdict,
    Patient,
    Severity,
    TimelineEvent,
    TimelineEventType,
)
from medai.repositories.memory import (
    InMemoryPatientRepository,
    InMemoryReportRepository,
    InMemoryTimelineRepository,
)
from medai.repositories.seed import create_seed_patients, create_seed_timeline_events


# ═══════════════════════════════════════════════════════════════
#  InMemoryPatientRepository
# ═══════════════════════════════════════════════════════════════

class TestInMemoryPatientRepository:

    @pytest.fixture
    def repo(self) -> InMemoryPatientRepository:
        return InMemoryPatientRepository()

    @pytest.fixture
    def sample_patient(self) -> Patient:
        return Patient(
            id="PT-TEST0001",
            name="Test Patient",
            date_of_birth=date(1990, 1, 15),
            gender=Gender.MALE,
            medical_record_number="MRN-TEST-001",
        )

    @pytest.mark.asyncio
    async def test_create_and_get(self, repo, sample_patient):
        created = await repo.create(sample_patient)
        assert created.id == "PT-TEST0001"
        assert created.name == "Test Patient"

        fetched = await repo.get("PT-TEST0001")
        assert fetched is not None
        assert fetched.name == "Test Patient"

    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_none(self, repo):
        result = await repo.get("PT-NONEXISTENT")
        assert result is None

    @pytest.mark.asyncio
    async def test_list_all_empty(self, repo):
        patients = await repo.list_all()
        assert patients == []

    @pytest.mark.asyncio
    async def test_list_all_after_creates(self, repo, sample_patient):
        await repo.create(sample_patient)
        p2 = Patient(id="PT-TEST0002", name="Second Patient", date_of_birth=date(1985, 6, 1))
        await repo.create(p2)

        patients = await repo.list_all()
        assert len(patients) == 2
        names = {p.name for p in patients}
        assert "Test Patient" in names
        assert "Second Patient" in names

    @pytest.mark.asyncio
    async def test_seed(self, repo):
        seed_patients = create_seed_patients()
        repo.seed(seed_patients)

        patients = await repo.list_all()
        assert len(patients) == 3

        maria = await repo.get("PT-DEMO0001")
        assert maria is not None
        assert maria.name == "Maria Ivanova"

    @pytest.mark.asyncio
    async def test_create_overwrites_existing_id(self, repo, sample_patient):
        """Creating a patient with an existing ID updates the record."""
        await repo.create(sample_patient)
        updated = Patient(
            id="PT-TEST0001", name="Updated Name", date_of_birth=date(1990, 1, 15)
        )
        await repo.create(updated)

        fetched = await repo.get("PT-TEST0001")
        assert fetched is not None
        assert fetched.name == "Updated Name"


# ═══════════════════════════════════════════════════════════════
#  InMemoryTimelineRepository
# ═══════════════════════════════════════════════════════════════

class TestInMemoryTimelineRepository:

    @pytest.fixture
    def repo(self) -> InMemoryTimelineRepository:
        return InMemoryTimelineRepository()

    @pytest.fixture
    def sample_event(self) -> TimelineEvent:
        return TimelineEvent(
            id="TL-TEST0001",
            patient_id="PT-TEST0001",
            date=datetime(2024, 6, 1, 9, 0),
            event_type=TimelineEventType.ENCOUNTER,
            summary="Test encounter",
        )

    @pytest.mark.asyncio
    async def test_add_and_get(self, repo, sample_event):
        added = await repo.add_event(sample_event)
        assert added.id == "TL-TEST0001"

        events = await repo.get_for_patient("PT-TEST0001")
        assert len(events) == 1
        assert events[0].summary == "Test encounter"

    @pytest.mark.asyncio
    async def test_get_for_nonexistent_patient(self, repo):
        events = await repo.get_for_patient("PT-NONEXISTENT")
        assert events == []

    @pytest.mark.asyncio
    async def test_events_sorted_newest_first(self, repo):
        e1 = TimelineEvent(
            id="TL-OLD",
            patient_id="PT-X",
            date=datetime(2024, 1, 1),
            event_type=TimelineEventType.LAB,
            summary="Old event",
        )
        e2 = TimelineEvent(
            id="TL-NEW",
            patient_id="PT-X",
            date=datetime(2024, 6, 1),
            event_type=TimelineEventType.IMAGING,
            summary="New event",
        )
        await repo.add_event(e1)
        await repo.add_event(e2)

        events = await repo.get_for_patient("PT-X")
        assert len(events) == 2
        assert events[0].id == "TL-NEW"  # Newest first
        assert events[1].id == "TL-OLD"

    @pytest.mark.asyncio
    async def test_events_isolated_per_patient(self, repo):
        e1 = TimelineEvent(
            id="TL-A1", patient_id="PT-A", date=datetime(2024, 1, 1),
            event_type=TimelineEventType.NOTE, summary="A event",
        )
        e2 = TimelineEvent(
            id="TL-B1", patient_id="PT-B", date=datetime(2024, 1, 1),
            event_type=TimelineEventType.NOTE, summary="B event",
        )
        await repo.add_event(e1)
        await repo.add_event(e2)

        a_events = await repo.get_for_patient("PT-A")
        b_events = await repo.get_for_patient("PT-B")
        assert len(a_events) == 1
        assert len(b_events) == 1
        assert a_events[0].summary == "A event"
        assert b_events[0].summary == "B event"

    @pytest.mark.asyncio
    async def test_seed(self, repo):
        seed_events = create_seed_timeline_events()
        repo.seed(seed_events)

        maria_events = await repo.get_for_patient("PT-DEMO0001")
        assert len(maria_events) == 3

        oleks_events = await repo.get_for_patient("PT-DEMO0002")
        assert len(oleks_events) == 3

        natalia_events = await repo.get_for_patient("PT-DEMO0003")
        assert len(natalia_events) == 2


# ═══════════════════════════════════════════════════════════════
#  InMemoryReportRepository
# ═══════════════════════════════════════════════════════════════

class TestInMemoryReportRepository:

    @pytest.fixture
    def repo(self) -> InMemoryReportRepository:
        return InMemoryReportRepository()

    @pytest.fixture
    def sample_report(self) -> FinalReport:
        return FinalReport(
            id="RPT-TEST0001",
            encounter_id="ENC-TEST",
            patient_id="PT-TEST0001",
            diagnosis="Test diagnosis",
            confidence=0.85,
            evidence_summary="Test evidence",
            timeline_impact="Test impact",
            plan=["Step 1", "Step 2"],
            findings=[
                Finding(
                    finding="Test finding",
                    confidence=0.9,
                    explanation="Explanation",
                    severity=Severity.MILD,
                ),
            ],
        )

    @pytest.mark.asyncio
    async def test_save_and_get(self, repo, sample_report):
        saved = await repo.save(sample_report)
        assert saved.id == "RPT-TEST0001"

        fetched = await repo.get("RPT-TEST0001")
        assert fetched is not None
        assert fetched.diagnosis == "Test diagnosis"

    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_none(self, repo):
        result = await repo.get("RPT-NONEXISTENT")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_approval_approved(self, repo, sample_report):
        await repo.save(sample_report)

        updated = await repo.update_approval("RPT-TEST0001", "approved", "Looks good")
        assert updated is not None
        assert updated.approval_status == ApprovalStatus.APPROVED
        assert updated.doctor_notes == "Looks good"

    @pytest.mark.asyncio
    async def test_update_approval_rejected(self, repo, sample_report):
        await repo.save(sample_report)

        updated = await repo.update_approval(
            "RPT-TEST0001", "rejected", "Need more data"
        )
        assert updated is not None
        assert updated.approval_status == ApprovalStatus.REJECTED
        assert updated.doctor_notes == "Need more data"

    @pytest.mark.asyncio
    async def test_update_approval_nonexistent(self, repo):
        result = await repo.update_approval("RPT-NONEXISTENT", "approved")
        assert result is None

    @pytest.mark.asyncio
    async def test_list_for_patient(self, repo):
        r1 = FinalReport(
            id="RPT-A1", encounter_id="E1", patient_id="PT-A",
            diagnosis="D1", confidence=0.8, evidence_summary="E",
            timeline_impact="T", plan=[], findings=[],
        )
        r2 = FinalReport(
            id="RPT-A2", encounter_id="E2", patient_id="PT-A",
            diagnosis="D2", confidence=0.9, evidence_summary="E",
            timeline_impact="T", plan=[], findings=[],
        )
        r3 = FinalReport(
            id="RPT-B1", encounter_id="E3", patient_id="PT-B",
            diagnosis="D3", confidence=0.7, evidence_summary="E",
            timeline_impact="T", plan=[], findings=[],
        )
        await repo.save(r1)
        await repo.save(r2)
        await repo.save(r3)

        a_reports = await repo.list_for_patient("PT-A")
        assert len(a_reports) == 2
        assert {r.id for r in a_reports} == {"RPT-A1", "RPT-A2"}

        b_reports = await repo.list_for_patient("PT-B")
        assert len(b_reports) == 1

        c_reports = await repo.list_for_patient("PT-C")
        assert len(c_reports) == 0


# ═══════════════════════════════════════════════════════════════
#  Seed Data Smoke Tests
# ═══════════════════════════════════════════════════════════════

class TestSeedData:
    def test_seed_patients_valid(self):
        patients = create_seed_patients()
        assert len(patients) == 3
        for p in patients:
            assert p.id.startswith("PT-DEMO")
            assert p.name
            assert p.date_of_birth

    def test_seed_events_valid(self):
        events = create_seed_timeline_events()
        assert len(events) == 8
        patient_ids = {e.patient_id for e in events}
        assert patient_ids == {"PT-DEMO0001", "PT-DEMO0002", "PT-DEMO0003"}

    def test_seed_events_reference_seed_patients(self):
        patients = create_seed_patients()
        events = create_seed_timeline_events()
        patient_ids = {p.id for p in patients}
        for e in events:
            assert e.patient_id in patient_ids, f"Event {e.id} references unknown patient"
