"""Case analysis endpoints — the main doctor-facing API."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from medai.api.dependencies import get_orchestrator, get_report_repository, get_timeline_repository
from medai.config import get_settings
from medai.domain.interfaces import BaseOrchestrator, BaseReportRepository
from medai.api.auth import get_current_user
from medai.domain.entities import TimelineEvent, TimelineEventType, User
from medai.domain.interfaces import BaseOrchestrator, BaseReportRepository, BaseTimelineRepository

from medai.domain.schemas import (
    CaseAnalysisRequest,
    CaseAnalysisResponse,
    ReportApprovalRequest,
    ReportApprovalResponse,
)
from medai.services.artifact_storage import ArtifactStorage
from medai.services.pipeline_events import (
    create_event_queue,
    emit_pipeline_done,
    pipeline_events_var,
)

_logger = structlog.get_logger()

router = APIRouter(prefix="/cases", tags=["cases"])


# ── Shared helpers ─────────────────────────────────────────────

def _sanitize_specialist_outputs(
    outputs: dict,
    artifact_store: ArtifactStorage,
    report_id: str,
) -> dict:
    """Create a frontend-safe copy of specialist_outputs.

    Replaces base64 data URIs with /storage/ URLs and strips embeddings.
    """
    import copy

    sanitized: dict = {}
    for tool_name, output in outputs.items():
        if not isinstance(output, dict):
            sanitized[tool_name] = output
            continue
        o = copy.deepcopy(output)
        # Remove large embedding arrays
        o.pop("embedding", None)
        # Replace attention_heatmap_url base64 → saved storage URL
        raw_heatmap = o.get("attention_heatmap_url") or ""
        if raw_heatmap.startswith("data:image/"):
            saved = artifact_store.save_data_uri(
                raw_heatmap, prefix=f"{tool_name}_top", report_id=report_id,
            )
            o["attention_heatmap_url"] = f"/storage/{saved}" if saved else None
        # Replace per-condition heatmap_data_uri base64 → saved storage URL
        for cs in o.get("condition_scores", []):
            if isinstance(cs, dict):
                uri = cs.get("heatmap_data_uri") or ""
                if uri.startswith("data:image/"):
                    label_slug = cs.get("label", "unknown").replace(" ", "_")[:30]
                    saved = artifact_store.save_data_uri(
                        uri, prefix=f"heatmap_{label_slug}", report_id=report_id,
                    )
                    cs["heatmap_data_uri"] = f"/storage/{saved}" if saved else None
        sanitized[tool_name] = o
    return sanitized


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

    # Persist the report — wrapped in try/except so the doctor still
    # gets the analysis result even if persistence fails.
    try:
        await report_repo.save(report)
    except Exception as e:
        import structlog
        structlog.get_logger().error(
            "report_save_failed",
            report_id=report.id,
            error=str(e),
        )
        # Continue — the report is still returned to the caller and
        # saved as a JSON artifact below.

    # Set up artifact storage for heatmaps
    settings = get_settings()
    artifact_store = ArtifactStorage(settings.storage_local_path)
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

    # Sanitize specialist outputs for frontend (strip base64, save to disk)
    sanitized_outputs = _sanitize_specialist_outputs(
        report.specialist_outputs, artifact_store, report.id,
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
        specialist_outputs=sanitized_outputs,
        pipeline_metrics=report.pipeline_metrics,
    )


# ── SSE — real-time pipeline progress ─────────────────────


def _build_response(report, artifact_store, current_user) -> CaseAnalysisResponse:
    """Shared response builder used by both sync and SSE endpoints."""
    heatmap_urls: list[str] = []
    specialist_summaries: dict[str, str] = {}
    for tool_name, output in report.specialist_outputs.items():
        if isinstance(output, dict):
            raw_heatmap = output.get("attention_heatmap_url") or ""
            if raw_heatmap.startswith("data:image/"):
                saved = artifact_store.save_data_uri(
                    raw_heatmap, prefix=f"{tool_name}_top", report_id=report.id,
                )
                if saved:
                    heatmap_urls.append(f"/storage/{saved}")
            elif raw_heatmap:
                heatmap_urls.append(raw_heatmap)

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

            if "assessment" in output:
                specialist_summaries[tool_name] = output["assessment"]
            elif "summary" in output:
                specialist_summaries[tool_name] = output["summary"]
            elif "timeline_context" in output:
                specialist_summaries[tool_name] = output["timeline_context"]
            elif "condition_scores" in output:
                scores = output["condition_scores"]
                model_id = (
                    output.get("inference", {}).get("model_id", "MedSigLIP")
                    if isinstance(output.get("inference"), dict) else "MedSigLIP"
                )
                lines = [f"Model: {model_id}"]
                if isinstance(scores, list):
                    for cs_ in sorted(scores, key=lambda s: s.get("probability", 0), reverse=True)[:5]:
                        lines.append(f"  {cs_.get('label', '?')}: {cs_.get('probability', 0):.1%}")
                specialist_summaries[tool_name] = "\n".join(lines)

    artifact_store.save_json_artifact(
        report.model_dump(mode="json"),
        filename="full_report.json",
        report_id=report.id,
    )

    # Sanitize specialist outputs for frontend
    sanitized_outputs = _sanitize_specialist_outputs(
        report.specialist_outputs, artifact_store, report.id,
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
        specialist_outputs=sanitized_outputs,
        pipeline_metrics=report.pipeline_metrics,
    )


@router.post("/analyze/stream")
async def analyze_case_stream(
    request: CaseAnalysisRequest,
    orchestrator: BaseOrchestrator = Depends(get_orchestrator),
    report_repo: BaseReportRepository = Depends(get_report_repository),
    timeline_repo: BaseTimelineRepository = Depends(get_timeline_repository),
    current_user: User = Depends(get_current_user),
):
    """SSE stream of pipeline progress events followed by the final result.

    Event types sent:
      - ``pipeline_start``  — analysis begins
      - ``phase_start``     — a pipeline phase starts (routing / judging / report)
      - ``tool_start``      — a specialist tool begins execution
      - ``tool_complete``   — a tool finished successfully (includes elapsed_s)
      - ``tool_error``      — a tool failed
      - ``phase_complete``  — a phase finished
      - ``result``          — the final CaseAnalysisResponse JSON
      - ``error``           — unrecoverable error
    """

    async def _event_stream():
        queue = create_event_queue()
        token = pipeline_events_var.set(queue)

        # Run the orchestrator in a background task so we can
        # drain events from the queue concurrently.
        result_future: asyncio.Future = asyncio.get_event_loop().create_future()

        async def _run_analysis():
            try:
                report = await orchestrator.analyze_case(request)
                # Persist
                try:
                    await report_repo.save(report)
                except Exception as e:
                    _logger.error("report_save_failed", report_id=report.id, error=str(e))

                settings = get_settings()
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

                artifact_store = ArtifactStorage(settings.storage_local_path)
                response = _build_response(report, artifact_store, current_user)
                result_future.set_result(response)
            except Exception as exc:
                result_future.set_exception(exc)
            finally:
                await emit_pipeline_done()

        analysis_task = asyncio.create_task(_run_analysis())

        try:
            # Drain the event queue, yielding SSE events
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=120)
                except asyncio.TimeoutError:
                    yield "event: ping\ndata: {}\n\n"
                    continue

                if event["type"] == "done":
                    break

                yield f"event: {event['type']}\ndata: {json.dumps(event)}\n\n"

            # Now yield the final result
            try:
                result = result_future.result()
                yield f"event: result\ndata: {result.model_dump_json()}\n\n"
            except Exception as exc:
                yield f"event: error\ndata: {json.dumps({'error': str(exc)})}\n\n"
        finally:
            pipeline_events_var.reset(token)
            if not analysis_task.done():
                analysis_task.cancel()

    return StreamingResponse(
        _event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
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

    settings = get_settings()
    artifact_store = ArtifactStorage(settings.storage_local_path)

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

    # Sanitize specialist outputs for frontend (strip base64, save to disk)
    sanitized_outputs = _sanitize_specialist_outputs(
        report.specialist_outputs, artifact_store, report.id,
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
        specialist_outputs=sanitized_outputs,
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
