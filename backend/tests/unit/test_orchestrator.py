"""Unit tests for the orchestrator and judge (mock mode).

Tests the full pipeline: route → dispatch → collect → judge → report
without calling any real APIs.
"""

from __future__ import annotations

import pytest

from medai.domain.entities import (
    ApprovalStatus,
    FinalReport,
    JudgeVerdict,
    ToolName,
)
from medai.domain.schemas import CaseAnalysisRequest
from medai.services.judge import MockJudge
from medai.services.orchestrator import MockOrchestrator
from medai.services.tool_registry import ToolRegistry
from medai.tools.mock import register_mock_tools


def _make_registry() -> ToolRegistry:
    registry = ToolRegistry()
    for tool in register_mock_tools().values():
        registry.register(tool)
    return registry


# ═══════════════════════════════════════════════════════════════
#  MockOrchestrator Tests
# ═══════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestMockOrchestrator:
    @pytest.mark.asyncio
    async def test_analyze_case_text_only(self):
        """Minimal case: text reasoning + history search (no images/audio)."""
        registry = _make_registry()
        judge = MockJudge()
        orchestrator = MockOrchestrator(tool_registry=registry, judge=judge)

        request = CaseAnalysisRequest(
            patient_id="PT-TEST-001",
            doctor_query="Assess for pneumonia",
            clinical_context="3-week productive cough, fever 38.5C",
        )

        report = await orchestrator.analyze_case(request)

        assert isinstance(report, FinalReport)
        assert report.patient_id == "PT-TEST-001"
        assert report.id.startswith("RPT-")
        assert report.diagnosis != ""
        assert 0 <= report.confidence <= 1
        assert report.approval_status == ApprovalStatus.PENDING
        assert report.judge_verdict is not None
        assert report.judge_verdict.verdict == JudgeVerdict.CONSENSUS

    @pytest.mark.asyncio
    async def test_analyze_case_with_image(self):
        """Case with image: triggers image_analysis + text_reasoning + history."""
        registry = _make_registry()
        judge = MockJudge()
        orchestrator = MockOrchestrator(tool_registry=registry, judge=judge)

        request = CaseAnalysisRequest(
            patient_id="PT-TEST-002",
            doctor_query="Rule out pneumonia",
            clinical_context="Persistent cough",
            image_urls=["s3://bucket/cxr.dcm"],
        )

        report = await orchestrator.analyze_case(request)

        assert isinstance(report, FinalReport)
        # Should have findings from image analysis
        assert len(report.findings) > 0
        # Should have specialist outputs from all called tools
        assert ToolName.IMAGE_ANALYSIS.value in report.specialist_outputs
        assert ToolName.TEXT_REASONING.value in report.specialist_outputs
        assert ToolName.HISTORY_SEARCH.value in report.specialist_outputs

    @pytest.mark.asyncio
    async def test_analyze_case_with_audio(self):
        """Case with audio: triggers audio_analysis in addition to text + history."""
        registry = _make_registry()
        judge = MockJudge()
        orchestrator = MockOrchestrator(tool_registry=registry, judge=judge)

        request = CaseAnalysisRequest(
            patient_id="PT-TEST-003",
            doctor_query="Evaluate breathing sounds",
            clinical_context="Suspected asthma",
            audio_urls=["s3://bucket/breathing.wav"],
        )

        report = await orchestrator.analyze_case(request)

        assert isinstance(report, FinalReport)
        assert ToolName.AUDIO_ANALYSIS.value in report.specialist_outputs

    @pytest.mark.asyncio
    async def test_analyze_case_full(self):
        """Full case: all modalities."""
        registry = _make_registry()
        judge = MockJudge()
        orchestrator = MockOrchestrator(tool_registry=registry, judge=judge)

        request = CaseAnalysisRequest(
            patient_id="PT-TEST-004",
            encounter_id="ENC-TEST-004",
            doctor_query="Complete assessment",
            clinical_context="Multi-modal evaluation",
            image_urls=["cxr.dcm"],
            audio_urls=["breath.wav"],
            patient_history_text="No prior issues",
            lab_results=[{"wbc": 14.2}],
        )

        report = await orchestrator.analyze_case(request)

        assert report.encounter_id == "ENC-TEST-004"
        assert len(report.specialist_outputs) == 4  # All 4 tools
        assert len(report.plan) > 0
        assert len(report.reasoning_trace) > 0


@pytest.mark.unit
class TestMockOrchestratorDispatch:
    @pytest.mark.asyncio
    async def test_dispatch_specific_tools(self):
        """Test dispatching specific tools directly."""
        registry = _make_registry()
        judge = MockJudge()
        orchestrator = MockOrchestrator(tool_registry=registry, judge=judge)

        results = await orchestrator.dispatch_tools(
            tool_names=[ToolName.IMAGE_ANALYSIS, ToolName.TEXT_REASONING],
            tool_inputs={
                ToolName.IMAGE_ANALYSIS: {"image_url": "test.png"},
                ToolName.TEXT_REASONING: {"clinical_context": "test"},
            },
        )

        assert ToolName.IMAGE_ANALYSIS.value in results.results
        assert ToolName.TEXT_REASONING.value in results.results
        assert len(results.errors) == 0

    @pytest.mark.asyncio
    async def test_dispatch_missing_tool(self):
        """Test dispatching a tool that isn't registered."""
        registry = ToolRegistry()  # empty!
        judge = MockJudge()
        orchestrator = MockOrchestrator(tool_registry=registry, judge=judge)

        results = await orchestrator.dispatch_tools(
            tool_names=[ToolName.IMAGE_ANALYSIS],
            tool_inputs={},
        )

        assert ToolName.IMAGE_ANALYSIS.value in results.errors


# ═══════════════════════════════════════════════════════════════
#  Report Structure Validation
# ═══════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestReportStructure:
    @pytest.mark.asyncio
    async def test_report_json_structure(self):
        """Validate the full report JSON matches the expected frontend contract."""
        registry = _make_registry()
        judge = MockJudge()
        orchestrator = MockOrchestrator(tool_registry=registry, judge=judge)

        request = CaseAnalysisRequest(
            patient_id="PT-JSON",
            doctor_query="Test report structure",
            clinical_context="Test context",
            image_urls=["test.png"],
        )

        report = await orchestrator.analyze_case(request)
        data = report.model_dump()

        # Top-level required fields
        required_fields = [
            "id", "encounter_id", "patient_id", "diagnosis",
            "confidence", "evidence_summary", "timeline_impact",
            "plan", "findings", "reasoning_trace",
            "specialist_outputs", "judge_verdict",
            "approval_status", "created_at",
        ]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Findings structure
        for finding in data["findings"]:
            assert "finding" in finding
            assert "confidence" in finding
            assert "explanation" in finding
            assert 0 <= finding["confidence"] <= 1

        # Judge verdict structure
        jv = data["judge_verdict"]
        assert jv["verdict"] in ("consensus", "conflict")
        assert 0 <= jv["confidence"] <= 1
