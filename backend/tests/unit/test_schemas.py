"""Unit tests for domain entities and schemas.

Validates that all Pydantic models serialize/deserialize correctly
and enforce their constraints.
"""

from __future__ import annotations

from datetime import date, datetime

import pytest

from medai.domain.entities import (
    ApprovalStatus,
    AudioAnalysisOutput,
    AudioSegment,
    EncounterType,
    EvidenceCitation,
    Finding,
    FinalReport,
    Gender,
    HistoryRecord,
    HistorySearchOutput,
    ImageAnalysisOutput,
    JudgeVerdict,
    JudgmentResult,
    Modality,
    Patient,
    Severity,
    SpecialistResults,
    TextReasoningOutput,
    TimelineEvent,
    TimelineEventType,
    ToolName,
)
from medai.domain.schemas import (
    CaseAnalysisRequest,
    CaseAnalysisResponse,
    HealthResponse,
)


# ═══════════════════════════════════════════════════════════════
#  Entity Tests
# ═══════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestPatient:
    def test_patient_creation_with_defaults(self):
        p = Patient(name="John Doe", date_of_birth=date(1990, 5, 15))
        assert p.name == "John Doe"
        assert p.id.startswith("PT-")
        assert p.gender == Gender.UNKNOWN

    def test_patient_serialization(self):
        p = Patient(name="Jane", date_of_birth=date(1985, 1, 1), gender=Gender.FEMALE)
        data = p.model_dump()
        assert data["name"] == "Jane"
        assert data["gender"] == "female"

        # Round-trip
        p2 = Patient.model_validate(data)
        assert p2.name == p.name


@pytest.mark.unit
class TestFinding:
    def test_finding_confidence_bounds(self):
        f = Finding(finding="test", confidence=0.5, explanation="test")
        assert f.confidence == 0.5

    def test_finding_confidence_out_of_bounds(self):
        with pytest.raises(Exception):  # ValidationError
            Finding(finding="test", confidence=1.5, explanation="test")

    def test_finding_with_region(self):
        f = Finding(
            finding="consolidation",
            confidence=0.89,
            explanation="Dense opacity",
            severity=Severity.MODERATE,
            region_bbox=[120, 340, 280, 480],
        )
        assert f.region_bbox == [120, 340, 280, 480]
        assert f.severity == Severity.MODERATE


# ═══════════════════════════════════════════════════════════════
#  Tool Output Tests
# ═══════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestImageAnalysisOutput:
    def test_full_output(self):
        output = ImageAnalysisOutput(
            modality_detected=Modality.XRAY,
            findings=[
                Finding(
                    finding="RLL consolidation",
                    confidence=0.89,
                    explanation="Dense opacity in right lower zone",
                    severity=Severity.MODERATE,
                )
            ],
            attention_heatmap_url="/heatmap.png",
            differential_diagnoses=["pneumonia"],
            recommended_followup=["Lateral CXR"],
        )
        data = output.model_dump()
        assert data["tool"] == "image_analysis"
        assert len(data["findings"]) == 1
        assert data["modality_detected"] == "xray"

    def test_json_serialization(self):
        output = ImageAnalysisOutput(
            modality_detected=Modality.CT,
            findings=[],
        )
        json_str = output.model_dump_json()
        assert '"image_analysis"' in json_str


@pytest.mark.unit
class TestTextReasoningOutput:
    def test_full_output(self):
        output = TextReasoningOutput(
            reasoning_chain=[{"step": 1, "thought": "Analysis"}],
            assessment="Pneumonia",
            confidence=0.87,
            evidence_citations=[
                EvidenceCitation(
                    source="lab_result",
                    source_type="lab",
                    relevant_excerpt="WBC elevated",
                )
            ],
            plan_suggestions=["Antibiotics"],
        )
        assert output.assessment == "Pneumonia"
        assert len(output.plan_suggestions) == 1


@pytest.mark.unit
class TestAudioAnalysisOutput:
    def test_full_output(self):
        output = AudioAnalysisOutput(
            audio_type="breathing",
            segments=[
                AudioSegment(
                    time_start=0.0, time_end=2.0,
                    classification="wheeze", confidence=0.78,
                )
            ],
            summary="Wheezing detected",
            abnormal_segment_timestamps=[0.0],
        )
        assert output.segments[0].classification == "wheeze"


@pytest.mark.unit
class TestHistorySearchOutput:
    def test_full_output(self):
        output = HistorySearchOutput(
            patient_id="PT-123",
            relevant_records=[
                HistoryRecord(
                    date=datetime(2024, 3, 15),
                    record_type="imaging",
                    summary="Clear CXR",
                    similarity_score=0.87,
                    clinical_relevance="Baseline comparison",
                )
            ],
            timeline_context="No prior respiratory issues",
        )
        assert output.patient_id == "PT-123"
        assert len(output.relevant_records) == 1


# ═══════════════════════════════════════════════════════════════
#  Judgment & Report Tests
# ═══════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestJudgmentResult:
    def test_consensus(self):
        j = JudgmentResult(
            verdict=JudgeVerdict.CONSENSUS,
            confidence=0.85,
            reasoning="All consistent",
        )
        assert j.verdict == JudgeVerdict.CONSENSUS
        assert j.requery_tools == []

    def test_conflict_with_requery(self):
        j = JudgmentResult(
            verdict=JudgeVerdict.CONFLICT,
            confidence=0.4,
            reasoning="Contradictions found",
            contradictions=["Image says X, text says Y"],
            requery_tools=[ToolName.IMAGE_ANALYSIS],
        )
        assert j.verdict == JudgeVerdict.CONFLICT
        assert ToolName.IMAGE_ANALYSIS in j.requery_tools


@pytest.mark.unit
class TestFinalReport:
    def test_report_creation(self):
        r = FinalReport(
            encounter_id="ENC-001",
            patient_id="PT-001",
            diagnosis="Pneumonia",
            confidence=0.87,
            evidence_summary="Elevated WBC + CXR consolidation",
            timeline_impact="New finding",
            plan=["Antibiotics"],
            findings=[],
        )
        assert r.id.startswith("RPT-")
        assert r.approval_status == ApprovalStatus.PENDING
        assert r.diagnosis == "Pneumonia"

    def test_report_json_roundtrip(self):
        r = FinalReport(
            encounter_id="ENC-001",
            patient_id="PT-001",
            diagnosis="Test",
            confidence=0.5,
            evidence_summary="Test",
            timeline_impact="Test",
            plan=[],
            findings=[],
        )
        json_str = r.model_dump_json()
        r2 = FinalReport.model_validate_json(json_str)
        assert r2.diagnosis == r.diagnosis


# ═══════════════════════════════════════════════════════════════
#  Schema Tests (API Request/Response)
# ═══════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestCaseAnalysisRequest:
    def test_minimal_request(self):
        req = CaseAnalysisRequest(
            patient_id="PT-001",
            doctor_query="What's wrong?",
        )
        assert req.patient_id == "PT-001"
        assert req.image_urls == []

    def test_full_request(self):
        req = CaseAnalysisRequest(
            patient_id="PT-001",
            encounter_id="ENC-001",
            image_urls=["s3://bucket/cxr.dcm"],
            audio_urls=["s3://bucket/cough.wav"],
            clinical_context="Persistent cough 3 weeks",
            doctor_query="Rule out pneumonia",
            patient_history_text="No prior respiratory issues",
            lab_results=[{"wbc": 14.2, "crp": 45}],
        )
        assert len(req.image_urls) == 1
        assert len(req.audio_urls) == 1


@pytest.mark.unit
class TestHealthResponse:
    def test_health(self):
        h = HealthResponse(
            version="0.1.0",
            tools_registered=["image_analysis", "text_reasoning"],
        )
        assert h.status == "ok"
        assert len(h.tools_registered) == 2
