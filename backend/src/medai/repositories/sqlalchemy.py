"""SQLAlchemy async repository implementations.

Each repository converts between Pydantic domain entities and
SQLAlchemy row models, keeping the domain layer persistence-agnostic.

All repos accept an AsyncSession injected per-request via FastAPI Depends().
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

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
from medai.domain.interfaces import (
    BasePatientRepository,
    BaseReportRepository,
    BaseTimelineRepository,
    BaseUserRepository,
)
from medai.repositories.models import (
    FinalReportRow,
    PatientRow,
    TimelineEventRow,
    UserRow,
)


# ═══════════════════════════════════════════════════════════════
#  User Repository
# ═══════════════════════════════════════════════════════════════

class SqlAlchemyUserRepository(BaseUserRepository):
    """PostgreSQL-backed user repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: str) -> User | None:
        row = await self._session.get(UserRow, user_id)
        return self._to_entity(row) if row else None

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(
            select(UserRow).where(UserRow.email == email)
        )
        row = result.scalar_one_or_none()
        return self._to_entity(row) if row else None

    async def create(self, user: User) -> User:
        row = self._to_row(user)
        self._session.add(row)
        await self._session.flush()
        return self._to_entity(row)

    async def list_all(self) -> list[User]:
        result = await self._session.execute(select(UserRow))
        return [self._to_entity(row) for row in result.scalars().all()]

    @staticmethod
    def _to_entity(row: UserRow) -> User:
        return User(
            id=row.id,
            email=row.email,
            hashed_password=row.hashed_password,
            name=row.name,
            role=UserRole(row.role),
            is_active=row.is_active,
            created_at=row.created_at,
        )

    @staticmethod
    def _to_row(user: User) -> UserRow:
        return UserRow(
            id=user.id,
            email=user.email,
            hashed_password=user.hashed_password,
            name=user.name,
            role=user.role.value if isinstance(user.role, UserRole) else user.role,
            is_active=user.is_active,
            created_at=user.created_at,
        )


# ═══════════════════════════════════════════════════════════════
#  Patient Repository
# ═══════════════════════════════════════════════════════════════

class SqlAlchemyPatientRepository(BasePatientRepository):
    """PostgreSQL-backed patient repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, patient_id: str) -> Patient | None:
        row = await self._session.get(PatientRow, patient_id)
        return self._to_entity(row) if row else None

    async def create(self, patient: Patient) -> Patient:
        row = self._to_row(patient)
        self._session.add(row)
        await self._session.flush()
        return self._to_entity(row)

    async def list_all(self) -> list[Patient]:
        result = await self._session.execute(select(PatientRow))
        return [self._to_entity(row) for row in result.scalars().all()]

    async def update(self, patient_id: str, **fields: Any) -> Patient | None:
        row = await self._session.get(PatientRow, patient_id)
        if row is None:
            return None
        for key, value in fields.items():
            if value is not None and hasattr(row, key):
                setattr(row, key, value)
        await self._session.flush()
        return self._to_entity(row)
    @staticmethod
    def _to_entity(row: PatientRow) -> Patient:
        return Patient(
            id=row.id,
            name=row.name,
            date_of_birth=date.fromisoformat(row.date_of_birth),
            gender=Gender(row.gender),
            medical_record_number=row.medical_record_number,
            created_at=row.created_at,
        )

    @staticmethod
    def _to_row(patient: Patient) -> PatientRow:
        return PatientRow(
            id=patient.id,
            name=patient.name,
            date_of_birth=patient.date_of_birth.isoformat(),
            gender=patient.gender.value,
            medical_record_number=patient.medical_record_number,
            created_at=patient.created_at,
        )


# ═══════════════════════════════════════════════════════════════
#  Timeline Repository
# ═══════════════════════════════════════════════════════════════

class SqlAlchemyTimelineRepository(BaseTimelineRepository):
    """PostgreSQL-backed timeline repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_for_patient(self, patient_id: str) -> list[TimelineEvent]:
        result = await self._session.execute(
            select(TimelineEventRow)
            .where(TimelineEventRow.patient_id == patient_id)
            .order_by(TimelineEventRow.date.desc())
        )
        return [self._to_entity(row) for row in result.scalars().all()]

    async def add_event(self, event: TimelineEvent) -> TimelineEvent:
        row = self._to_row(event)
        self._session.add(row)
        await self._session.flush()
        return self._to_entity(row)

    @staticmethod
    def _to_entity(row: TimelineEventRow) -> TimelineEvent:
        return TimelineEvent(
            id=row.id,
            patient_id=row.patient_id,
            date=row.date,
            event_type=TimelineEventType(row.event_type),
            summary=row.summary,
            source_id=row.source_id,
            source_type=row.source_type,
            metadata=row.metadata_ or {},
        )

    @staticmethod
    def _to_row(event: TimelineEvent) -> TimelineEventRow:
        return TimelineEventRow(
            id=event.id,
            patient_id=event.patient_id,
            date=event.date,
            event_type=event.event_type.value,
            summary=event.summary,
            source_id=event.source_id,
            source_type=event.source_type,
            metadata_=event.metadata,
        )


# ═══════════════════════════════════════════════════════════════
#  Report Repository
# ═══════════════════════════════════════════════════════════════

def _serialize_findings(findings: list[Finding]) -> list[dict[str, Any]]:
    """Serialize Finding list to JSON-safe dicts."""
    return [f.model_dump(mode="json") for f in findings]


def _deserialize_findings(data: list[dict[str, Any]] | None) -> list[Finding]:
    """Deserialize Finding list from JSON dicts."""
    if not data:
        return []
    return [Finding(**d) for d in data]


def _serialize_judgment(verdict: JudgmentResult | None) -> dict[str, Any] | None:
    """Serialize JudgmentResult to JSON-safe dict."""
    if verdict is None:
        return None
    return verdict.model_dump(mode="json")


def _deserialize_judgment(data: dict[str, Any] | None) -> JudgmentResult | None:
    """Deserialize JudgmentResult from JSON dict."""
    if not data:
        return None
    return JudgmentResult(**data)


def _serialize_metrics(metrics: PipelineMetrics | None) -> dict[str, Any] | None:
    """Serialize PipelineMetrics to JSON-safe dict."""
    if metrics is None:
        return None
    return metrics.model_dump(mode="json")


def _deserialize_metrics(data: dict[str, Any] | None) -> PipelineMetrics | None:
    """Deserialize PipelineMetrics from JSON dict."""
    if not data:
        return None
    return PipelineMetrics(**data)


class SqlAlchemyReportRepository(BaseReportRepository):
    """PostgreSQL-backed report repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, report_id: str) -> FinalReport | None:
        row = await self._session.get(FinalReportRow, report_id)
        return self._to_entity(row) if row else None

    async def save(self, report: FinalReport) -> FinalReport:
        row = self._to_row(report)
        merged = await self._session.merge(row)
        await self._session.flush()
        return self._to_entity(merged)

    async def update_approval(
        self, report_id: str, status: str, doctor_notes: str | None = None,
        edits: dict[str, Any] | None = None,
    ) -> FinalReport | None:
        values: dict[str, Any] = {"approval_status": status}
        if doctor_notes is not None:
            values["doctor_notes"] = doctor_notes

        # Apply edits to mutable report fields
        if edits:
            editable_fields = {
                "diagnosis", "evidence_summary", "plan", "timeline_impact",
            }
            for field, value in edits.items():
                if field in editable_fields:
                    values[field] = value

        await self._session.execute(
            update(FinalReportRow)
            .where(FinalReportRow.id == report_id)
            .values(**values)
        )
        await self._session.flush()

        # Re-fetch to return updated entity
        row = await self._session.get(FinalReportRow, report_id)
        return self._to_entity(row) if row else None

    async def list_for_patient(self, patient_id: str) -> list[FinalReport]:
        result = await self._session.execute(
            select(FinalReportRow).where(FinalReportRow.patient_id == patient_id)
        )
        return [self._to_entity(row) for row in result.scalars().all()]

    @staticmethod
    def _to_entity(row: FinalReportRow) -> FinalReport:
        return FinalReport(
            id=row.id,
            encounter_id=row.encounter_id,
            patient_id=row.patient_id,
            diagnosis=row.diagnosis,
            confidence=row.confidence,
            confidence_method=ConfidenceMethod(row.confidence_method),
            evidence_summary=row.evidence_summary,
            timeline_impact=row.timeline_impact,
            plan=row.plan or [],
            findings=_deserialize_findings(row.findings),
            reasoning_trace=row.reasoning_trace or [],
            specialist_outputs=row.specialist_outputs or {},
            judge_verdict=_deserialize_judgment(row.judge_verdict),
            approval_status=ApprovalStatus(row.approval_status),
            created_at=row.created_at,
            doctor_notes=row.doctor_notes,
            pipeline_metrics=_deserialize_metrics(row.pipeline_metrics),
        )

    @staticmethod
    def _to_row(report: FinalReport) -> FinalReportRow:
        return FinalReportRow(
            id=report.id,
            encounter_id=report.encounter_id,
            patient_id=report.patient_id,
            diagnosis=report.diagnosis,
            confidence=report.confidence,
            confidence_method=report.confidence_method.value,
            evidence_summary=report.evidence_summary,
            timeline_impact=report.timeline_impact,
            plan=report.plan,
            findings=_serialize_findings(report.findings),
            reasoning_trace=report.reasoning_trace,
            specialist_outputs=report.specialist_outputs,
            judge_verdict=_serialize_judgment(report.judge_verdict),
            approval_status=report.approval_status.value,
            created_at=report.created_at,
            doctor_notes=report.doctor_notes,
            pipeline_metrics=_serialize_metrics(report.pipeline_metrics),
        )
