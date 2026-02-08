"""In-memory repository implementations.

Fast, zero-dependency storage for development and testing.
Same interface as future PostgreSQL/SQLAlchemy repos —
swap via dependency injection, zero code changes needed.
"""

from __future__ import annotations

from typing import Any

from medai.domain.entities import (
    ApprovalStatus,
    FinalReport,
    Patient,
    TimelineEvent,
)
from medai.domain.interfaces import (
    BasePatientRepository,
    BaseReportRepository,
    BaseTimelineRepository,
)


class InMemoryPatientRepository(BasePatientRepository):
    """In-memory patient store."""

    def __init__(self) -> None:
        self._store: dict[str, Patient] = {}

    async def get(self, patient_id: str) -> Patient | None:
        return self._store.get(patient_id)

    async def create(self, patient: Patient) -> Patient:
        self._store[patient.id] = patient
        return patient

    async def list_all(self) -> list[Patient]:
        return list(self._store.values())

    async def update(self, patient_id: str, **fields: Any) -> Patient | None:
        patient = self._store.get(patient_id)
        if patient is None:
            return None
        for key, value in fields.items():
            if value is not None and hasattr(patient, key):
                setattr(patient, key, value)
        return patient

    def seed(self, patients: list[Patient]) -> None:
        """Seed the store with initial data (for dev/testing)."""
        for p in patients:
            self._store[p.id] = p


class InMemoryTimelineRepository(BaseTimelineRepository):
    """In-memory timeline store."""

    def __init__(self) -> None:
        self._store: dict[str, list[TimelineEvent]] = {}  # patient_id → events

    async def get_for_patient(self, patient_id: str) -> list[TimelineEvent]:
        events = self._store.get(patient_id, [])
        return sorted(events, key=lambda e: e.date, reverse=True)

    async def add_event(self, event: TimelineEvent) -> TimelineEvent:
        if event.patient_id not in self._store:
            self._store[event.patient_id] = []
        self._store[event.patient_id].append(event)
        return event

    def seed(self, events: list[TimelineEvent]) -> None:
        """Seed with initial timeline data."""
        for e in events:
            if e.patient_id not in self._store:
                self._store[e.patient_id] = []
            self._store[e.patient_id].append(e)


class InMemoryReportRepository(BaseReportRepository):
    """In-memory report store."""

    def __init__(self) -> None:
        self._store: dict[str, FinalReport] = {}

    async def get(self, report_id: str) -> FinalReport | None:
        return self._store.get(report_id)

    async def save(self, report: FinalReport) -> FinalReport:
        self._store[report.id] = report
        return report

    async def update_approval(
        self, report_id: str, status: str, doctor_notes: str | None = None
    ) -> FinalReport | None:
        report = self._store.get(report_id)
        if report is None:
            return None
        # Pydantic models are mutable by default in v2
        report.approval_status = ApprovalStatus(status)
        if doctor_notes is not None:
            report.doctor_notes = doctor_notes
        return report

    async def list_for_patient(self, patient_id: str) -> list[FinalReport]:
        return [r for r in self._store.values() if r.patient_id == patient_id]
