"""Case analysis endpoints — the main doctor-facing API."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from medai.api.auth import get_current_user
from medai.api.dependencies import get_orchestrator, get_report_repository, get_timeline_repository
from medai.domain.entities import TimelineEvent, TimelineEventType, User
from medai.domain.interfaces import BaseOrchestrator, BaseReportRepository, BaseTimelineRepository
from medai.domain.schemas import (
    CaseAnalysisRequest,
    CaseAnalysisResponse,
    ReportApprovalRequest,
    ReportApprovalResponse,
)

router = APIRouter(prefix="/cases", tags=["cases"])


@router.post("/analyze", response_model=CaseAnalysisResponse)
async def analyze_case(
    request: CaseAnalysisRequest,
    orchestrator: BaseOrchestrator = Depends(get_orchestrator),
    report_repo: BaseReportRepository = Depends(get_report_repository),
    timeline_repo: BaseTimelineRepository = Depends(get_timeline_repository),
    current_user: User = Depends(get_current_user),
) -> CaseAnalysisResponse:
    """Submit a patient case for AI analysis.

    The orchestrator will:
    1. Route the case to appropriate specialist tools
    2. Run tools in parallel
    3. Judge consensus across tool outputs
    4. Generate a final structured report with explainability artifacts

    The report is automatically persisted for later retrieval/approval.
    """
    try:
        report = await orchestrator.analyze_case(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")

    # Persist the report
    await report_repo.save(report)

    # Create a timeline event for the patient
    await timeline_repo.add_event(
        TimelineEvent(
            patient_id=request.patient_id,
            date=report.created_at,
            event_type=TimelineEventType.AI_REPORT,
            summary=f"AI Analysis: {report.diagnosis} ({report.confidence:.0%} confidence)",
            source_id=report.id,
            source_type="ai_report",
            metadata={
                "doctor_id": current_user.id,
                "doctor_name": current_user.name,
                "confidence": report.confidence,
            },
        )
    )

    # Map domain report → API response
    heatmap_urls = []
    specialist_summaries = {}
    for tool_name, output in report.specialist_outputs.items():
        if isinstance(output, dict):
            if "attention_heatmap_url" in output and output["attention_heatmap_url"]:
                heatmap_urls.append(output["attention_heatmap_url"])
            # Create short summary per tool
            if "assessment" in output:
                specialist_summaries[tool_name] = output["assessment"]
            elif "summary" in output:
                specialist_summaries[tool_name] = output["summary"]
            elif "timeline_context" in output:
                specialist_summaries[tool_name] = output["timeline_context"]

    return CaseAnalysisResponse(
        report_id=report.id,
        encounter_id=report.encounter_id,
        patient_id=report.patient_id,
        diagnosis=report.diagnosis,
        confidence=report.confidence,
        confidence_method=report.confidence_method,
        evidence_summary=report.evidence_summary,
        timeline_impact=report.timeline_impact,
        plan=report.plan,
        findings=report.findings,
        reasoning_trace=report.reasoning_trace,
        judge_verdict=report.judge_verdict,
        approval_status=report.approval_status,
        created_at=report.created_at,
        heatmap_urls=heatmap_urls,
        specialist_summaries=specialist_summaries,
        pipeline_metrics=report.pipeline_metrics,
    )


@router.get("/reports/{report_id}", response_model=CaseAnalysisResponse)
async def get_report(
    report_id: str,
    report_repo: BaseReportRepository = Depends(get_report_repository),
    _current_user: User = Depends(get_current_user),
) -> CaseAnalysisResponse:
    """Retrieve a previously generated report by ID."""
    report = await report_repo.get(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")

    # Re-extract specialist summaries
    heatmap_urls = []
    specialist_summaries = {}
    for tool_name, output in report.specialist_outputs.items():
        if isinstance(output, dict):
            if "attention_heatmap_url" in output and output["attention_heatmap_url"]:
                heatmap_urls.append(output["attention_heatmap_url"])
            if "assessment" in output:
                specialist_summaries[tool_name] = output["assessment"]
            elif "summary" in output:
                specialist_summaries[tool_name] = output["summary"]
            elif "timeline_context" in output:
                specialist_summaries[tool_name] = output["timeline_context"]

    return CaseAnalysisResponse(
        report_id=report.id,
        encounter_id=report.encounter_id,
        patient_id=report.patient_id,
        diagnosis=report.diagnosis,
        confidence=report.confidence,
        confidence_method=report.confidence_method,
        evidence_summary=report.evidence_summary,
        timeline_impact=report.timeline_impact,
        plan=report.plan,
        findings=report.findings,
        reasoning_trace=report.reasoning_trace,
        judge_verdict=report.judge_verdict,
        approval_status=report.approval_status,
        created_at=report.created_at,
        heatmap_urls=heatmap_urls,
        specialist_summaries=specialist_summaries,
        pipeline_metrics=report.pipeline_metrics,
    )


@router.post("/approve", response_model=ReportApprovalResponse)
async def approve_report(
    request: ReportApprovalRequest,
    report_repo: BaseReportRepository = Depends(get_report_repository),
    timeline_repo: BaseTimelineRepository = Depends(get_timeline_repository),
    current_user: User = Depends(get_current_user),
) -> ReportApprovalResponse:
    """Doctor approves, edits, or rejects an AI report.

    Updates the report's approval status in the database.
    If edits are provided, they are applied to mutable report fields.
    """
    report = await report_repo.update_approval(
        report_id=request.report_id,
        status=request.status.value,
        doctor_notes=request.doctor_notes,
        edits=request.edits,
    )
    if report is None:
        raise HTTPException(
            status_code=404,
            detail=f"Report {request.report_id} not found",
        )

    # Create a timeline event for the approval decision
    status_label = {
        "approved": "Approved",
        "rejected": "Rejected",
        "edited": "Approved with Edits",
    }.get(request.status.value, request.status.value)

    await timeline_repo.add_event(
        TimelineEvent(
            patient_id=report.patient_id,
            date=datetime.utcnow(),
            event_type=TimelineEventType.NOTE,
            summary=f"Report {status_label} by Dr. {current_user.name}: {report.diagnosis}",
            source_id=report.id,
            source_type="approval",
            metadata={
                "doctor_id": current_user.id,
                "doctor_name": current_user.name,
                "approval_status": request.status.value,
                "doctor_notes": request.doctor_notes,
            },
        )
    )

    return ReportApprovalResponse(
        report_id=report.id,
        status=report.approval_status,
        updated_at=datetime.utcnow(),
    )
