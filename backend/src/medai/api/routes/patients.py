"""Patient endpoints — CRUD + timeline + reports lookup."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException

from medai.api.dependencies import (
    get_patient_repository,
    get_report_repository,
    get_timeline_repository,
)
from medai.domain.entities import Gender, Patient
from medai.domain.interfaces import (
    BasePatientRepository,
    BaseReportRepository,
    BaseTimelineRepository,
)
from medai.domain.schemas import (
    PatientCreateRequest,
    PatientListResponse,
    PatientReportsResponse,
    PatientSummary,
    PatientTimelineResponse,
    ReportSummary,
    TimelineEventResponse,
)

router = APIRouter(prefix="/patients", tags=["patients"])


# ── Helpers ────────────────────────────────────────────────

def _patient_to_summary(p: Patient) -> PatientSummary:
    return PatientSummary(
        id=p.id,
        name=p.name,
        date_of_birth=p.date_of_birth.isoformat(),
        gender=p.gender.value,
        medical_record_number=p.medical_record_number,
        created_at=p.created_at,
    )


# ── Endpoints ──────────────────────────────────────────────

@router.get("", response_model=PatientListResponse)
async def list_patients(
    repo: BasePatientRepository = Depends(get_patient_repository),
) -> PatientListResponse:
    """List all patients."""
    patients = await repo.list_all()
    summaries = [_patient_to_summary(p) for p in patients]
    return PatientListResponse(patients=summaries, count=len(summaries))


@router.post("", response_model=PatientSummary, status_code=201)
async def create_patient(
    body: PatientCreateRequest,
    repo: BasePatientRepository = Depends(get_patient_repository),
) -> PatientSummary:
    """Create a new patient record."""
    patient = Patient(
        name=body.name,
        date_of_birth=date.fromisoformat(body.date_of_birth),
        gender=Gender(body.gender),
        medical_record_number=body.medical_record_number,
    )
    created = await repo.create(patient)
    return _patient_to_summary(created)


@router.get("/{patient_id}", response_model=PatientSummary)
async def get_patient(
    patient_id: str,
    repo: BasePatientRepository = Depends(get_patient_repository),
) -> PatientSummary:
    """Get a single patient by ID."""
    patient = await repo.get(patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")
    return _patient_to_summary(patient)


@router.get("/{patient_id}/timeline", response_model=PatientTimelineResponse)
async def get_patient_timeline(
    patient_id: str,
    patient_repo: BasePatientRepository = Depends(get_patient_repository),
    timeline_repo: BaseTimelineRepository = Depends(get_timeline_repository),
) -> PatientTimelineResponse:
    """Get the full timeline for a patient (newest first)."""
    # Verify patient exists
    patient = await patient_repo.get(patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")

    events = await timeline_repo.get_for_patient(patient_id)
    event_responses = [
        TimelineEventResponse(
            id=e.id,
            date=e.date,
            event_type=e.event_type.value,
            summary=e.summary,
            source_type=e.source_type,
            metadata=e.metadata,
        )
        for e in events
    ]
    return PatientTimelineResponse(
        patient_id=patient_id,
        events=event_responses,
        count=len(event_responses),
    )


@router.get("/{patient_id}/reports", response_model=PatientReportsResponse)
async def get_patient_reports(
    patient_id: str,
    patient_repo: BasePatientRepository = Depends(get_patient_repository),
    report_repo: BaseReportRepository = Depends(get_report_repository),
) -> PatientReportsResponse:
    """Get all AI reports for a patient."""
    patient = await patient_repo.get(patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")

    reports = await report_repo.list_for_patient(patient_id)
    summaries = [
        ReportSummary(
            report_id=r.id,
            encounter_id=r.encounter_id,
            diagnosis=r.diagnosis,
            confidence=r.confidence,
            approval_status=r.approval_status.value,
            created_at=r.created_at,
        )
        for r in reports
    ]
    return PatientReportsResponse(
        patient_id=patient_id,
        reports=summaries,
        count=len(summaries),
    )
