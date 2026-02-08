"""Case analysis endpoints — the main doctor-facing API."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from medai.api.dependencies import get_orchestrator, get_report_repository
from medai.config import get_settings
from medai.domain.interfaces import BaseOrchestrator, BaseReportRepository
from medai.domain.schemas import (
    CaseAnalysisRequest,
    CaseAnalysisResponse,
    ReportApprovalRequest,
    ReportApprovalResponse,
)
from medai.services.artifact_storage import ArtifactStorage

router = APIRouter(prefix="/cases", tags=["cases"])


@router.post("/analyze", response_model=CaseAnalysisResponse)
async def analyze_case(
    request: CaseAnalysisRequest,
    orchestrator: BaseOrchestrator = Depends(get_orchestrator),
    report_repo: BaseReportRepository = Depends(get_report_repository),
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

    # Set up artifact storage for heatmaps
    settings = get_settings()
    artifact_store = ArtifactStorage(settings.storage_local_path)

    # Map domain report → API response
    heatmap_urls = []
    specialist_summaries = {}
    for tool_name, output in report.specialist_outputs.items():
        if isinstance(output, dict):
            # Top-level attention_heatmap_url
            raw_heatmap = output.get("attention_heatmap_url") or ""
            if raw_heatmap.startswith("data:image/"):
                saved = artifact_store.save_data_uri(
                    raw_heatmap, prefix=f"{tool_name}_top", report_id=report.id,
                )
                if saved:
                    heatmap_urls.append(f"/storage/{saved}")
            elif raw_heatmap:
                heatmap_urls.append(raw_heatmap)

            # Per-condition heatmaps from image_explainability
            for cs in output.get("condition_scores", []):
                if isinstance(cs, dict) and cs.get("heatmap_data_uri", ""):
                    uri = cs["heatmap_data_uri"]
                    label_slug = cs.get("label", "unknown").replace(" ", "_")[:30]
                    if uri.startswith("data:image/"):
                        saved = artifact_store.save_data_uri(
                            uri, prefix=f"heatmap_{label_slug}", report_id=report.id,
                        )
                        if saved:
                            heatmap_urls.append(f"/storage/{saved}")
                    elif uri:
                        heatmap_urls.append(uri)

            # Create short summary per tool
            if "assessment" in output:
                specialist_summaries[tool_name] = output["assessment"]
            elif "summary" in output:
                specialist_summaries[tool_name] = output["summary"]
            elif "timeline_context" in output:
                specialist_summaries[tool_name] = output["timeline_context"]
            elif "condition_scores" in output:
                # image_explainability — build a readable synopsis
                scores = output["condition_scores"]
                model_id = output.get("inference", {}).get("model_id", "MedSigLIP") if isinstance(output.get("inference"), dict) else "MedSigLIP"
                lines = [f"Model: {model_id}"]
                if isinstance(scores, list):
                    for cs in sorted(scores, key=lambda s: s.get("probability", 0), reverse=True)[:5]:
                        label = cs.get("label", "?")
                        prob = cs.get("probability", 0)
                        lines.append(f"  {label}: {prob:.1%}")
                specialist_summaries[tool_name] = "\n".join(lines)

    # Save full report as structured JSON artifact
    artifact_store.save_json_artifact(
        report.model_dump(mode="json"),
        filename="full_report.json",
        report_id=report.id,
    )

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
            for cs in output.get("condition_scores", []):
                if isinstance(cs, dict) and cs.get("heatmap_data_uri"):
                    heatmap_urls.append(cs["heatmap_data_uri"])
            if "assessment" in output:
                specialist_summaries[tool_name] = output["assessment"]
            elif "summary" in output:
                specialist_summaries[tool_name] = output["summary"]
            elif "timeline_context" in output:
                specialist_summaries[tool_name] = output["timeline_context"]
            elif "condition_scores" in output:
                scores = output["condition_scores"]
                model_id = output.get("inference", {}).get("model_id", "MedSigLIP") if isinstance(output.get("inference"), dict) else "MedSigLIP"
                lines = [f"Model: {model_id}"]
                for cs in sorted(scores, key=lambda s: s.get("probability", 0), reverse=True)[:5] if isinstance(scores, list) else []:
                    label = cs.get("label", "?")
                    prob = cs.get("probability", 0)
                    lines.append(f"  {label}: {prob:.1%}")
                specialist_summaries[tool_name] = "\n".join(lines)

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
) -> ReportApprovalResponse:
    """Doctor approves, edits, or rejects an AI report.

    Updates the report's approval status in the database.
    """
    report = await report_repo.update_approval(
        report_id=request.report_id,
        status=request.status.value,
        doctor_notes=request.doctor_notes,
    )
    if report is None:
        raise HTTPException(
            status_code=404,
            detail=f"Report {request.report_id} not found",
        )

    return ReportApprovalResponse(
        report_id=report.id,
        status=report.approval_status,
        updated_at=datetime.utcnow(),
    )
