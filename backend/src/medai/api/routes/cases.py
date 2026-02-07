"""Case analysis endpoints — the main doctor-facing API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from medai.api.dependencies import get_orchestrator
from medai.domain.interfaces import BaseOrchestrator
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
) -> CaseAnalysisResponse:
    """Submit a patient case for AI analysis.

    The orchestrator will:
    1. Route the case to appropriate specialist tools
    2. Run tools in parallel
    3. Judge consensus across tool outputs
    4. Generate a final structured report with explainability artifacts
    """
    try:
        report = await orchestrator.analyze_case(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")

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
    )


@router.post("/approve", response_model=ReportApprovalResponse)
async def approve_report(
    request: ReportApprovalRequest,
) -> ReportApprovalResponse:
    """Doctor approves, edits, or rejects an AI report.

    TODO: Implement with database persistence.
    """
    from datetime import datetime

    # Placeholder — will be backed by ReportRepository
    return ReportApprovalResponse(
        report_id=request.report_id,
        status=request.status,
        updated_at=datetime.utcnow(),
    )
