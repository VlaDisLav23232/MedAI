"""Unit tests for HTTP-based tool implementations.

Uses respx to mock HTTP endpoints — no real servers needed.
Validates:
- Request payload construction
- Response parsing into typed ToolOutput
- Retry logic on failures
- Timeout handling
- Error propagation
"""

from __future__ import annotations

import pytest
import httpx
import respx

from medai.domain.entities import (
    ImageAnalysisOutput,
    TextReasoningOutput,
    AudioAnalysisOutput,
    HistorySearchOutput,
    Modality,
    Severity,
    ToolName,
)
from medai.tools.http import (
    HttpImageAnalysisTool,
    HttpTextReasoningTool,
    HttpAudioAnalysisTool,
    HttpHistorySearchTool,
    register_http_tools,
)
from medai.config import Settings


MOCK_ENDPOINT = "http://mock-model:8010"


# ═══════════════════════════════════════════════════════════════
#  HttpImageAnalysisTool
# ═══════════════════════════════════════════════════════════════


class TestHttpImageAnalysisTool:
    @pytest.fixture
    def tool(self) -> HttpImageAnalysisTool:
        return HttpImageAnalysisTool(endpoint=MOCK_ENDPOINT, max_retries=0)

    @pytest.mark.asyncio
    @respx.mock
    async def test_successful_image_analysis(self, tool):
        respx.post(f"{MOCK_ENDPOINT}").mock(
            return_value=httpx.Response(
                200,
                json={
                    "modality_detected": "xray",
                    "findings": [
                        {
                            "finding": "Consolidation in RLL",
                            "confidence": 0.92,
                            "explanation": "Dense opacity right lower zone",
                            "severity": "moderate",
                        }
                    ],
                    "attention_heatmap_url": "/heatmaps/001.png",
                    "embedding_id": "emb-001",
                    "differential_diagnoses": ["pneumonia", "atelectasis"],
                    "recommended_followup": ["Lateral CXR"],
                },
            )
        )

        result = await tool.execute(
            image_url="http://images/chest.png",
            clinical_context="Persistent cough 3 weeks",
        )

        assert isinstance(result, ImageAnalysisOutput)
        assert result.modality_detected == Modality.XRAY
        assert len(result.findings) == 1
        assert result.findings[0].finding == "Consolidation in RLL"
        assert result.findings[0].confidence == 0.92
        assert result.findings[0].severity == Severity.MODERATE
        assert result.findings[0].region_bbox is None  # No longer populated by image tool
        assert result.attention_heatmap_url == "/heatmaps/001.png"
        assert "pneumonia" in result.differential_diagnoses

    @pytest.mark.asyncio
    @respx.mock
    async def test_empty_findings(self, tool):
        respx.post(f"{MOCK_ENDPOINT}").mock(
            return_value=httpx.Response(200, json={"modality_detected": "ct", "findings": []})
        )
        result = await tool.execute(image_url="http://images/ct.png")
        assert isinstance(result, ImageAnalysisOutput)
        assert result.modality_detected == Modality.CT
        assert result.findings == []

    @pytest.mark.asyncio
    @respx.mock
    async def test_modality_normalization(self, tool):
        """Model returns 'chest x-ray' which is not a valid Modality enum value."""
        respx.post(f"{MOCK_ENDPOINT}").mock(
            return_value=httpx.Response(200, json={"modality_detected": "chest x-ray", "findings": []})
        )
        result = await tool.execute(image_url="http://images/cxr.png")
        assert result.modality_detected == Modality.XRAY  # normalized, not crash

    @pytest.mark.asyncio
    @respx.mock
    async def test_unknown_modality_falls_back(self, tool):
        """Completely unknown modality falls back to OTHER."""
        respx.post(f"{MOCK_ENDPOINT}").mock(
            return_value=httpx.Response(200, json={"modality_detected": "quantum_scan_3000", "findings": []})
        )
        result = await tool.execute(image_url="http://images/q.png")
        assert result.modality_detected == Modality.OTHER

    def test_interface_compliance(self, tool):
        assert tool.name == ToolName.IMAGE_ANALYSIS
        assert "image" in tool.description.lower()
        schema = tool.input_schema
        assert schema["required"] == ["image_url"]

    def test_claude_tool_definition(self, tool):
        defn = tool.to_claude_tool_definition()
        assert defn["name"] == "image_analysis"


# ═══════════════════════════════════════════════════════════════
#  HttpTextReasoningTool
# ═══════════════════════════════════════════════════════════════


class TestHttpTextReasoningTool:
    @pytest.fixture
    def tool(self) -> HttpTextReasoningTool:
        return HttpTextReasoningTool(endpoint=MOCK_ENDPOINT, max_retries=0)

    @pytest.mark.asyncio
    @respx.mock
    async def test_successful_text_reasoning(self, tool):
        respx.post(f"{MOCK_ENDPOINT}").mock(
            return_value=httpx.Response(
                200,
                json={
                    "reasoning_chain": [
                        {"step": 1, "thought": "Patient presents with cough"},
                    ],
                    "assessment": "Community-acquired pneumonia",
                    "confidence": 0.87,
                    "evidence_citations": [
                        {
                            "source": "lab_2024",
                            "source_type": "lab_result",
                            "relevant_excerpt": "WBC 14.2k elevated",
                            "date": "2024-06-01T00:00:00",
                        }
                    ],
                    "plan_suggestions": ["Amoxicillin BID x7d"],
                    "contraindication_flags": [],
                },
            )
        )

        result = await tool.execute(clinical_context="3-week cough, fever")
        assert isinstance(result, TextReasoningOutput)
        assert result.assessment == "Community-acquired pneumonia"
        assert result.confidence == 0.87
        assert len(result.evidence_citations) == 1
        assert result.plan_suggestions == ["Amoxicillin BID x7d"]

    def test_interface_compliance(self, tool):
        assert tool.name == ToolName.TEXT_REASONING
        assert tool.input_schema["required"] == ["clinical_context"]


# ═══════════════════════════════════════════════════════════════
#  HttpAudioAnalysisTool
# ═══════════════════════════════════════════════════════════════


class TestHttpAudioAnalysisTool:
    @pytest.fixture
    def tool(self) -> HttpAudioAnalysisTool:
        return HttpAudioAnalysisTool(endpoint=MOCK_ENDPOINT, max_retries=0)

    @pytest.mark.asyncio
    @respx.mock
    async def test_successful_audio_analysis(self, tool):
        respx.post(f"{MOCK_ENDPOINT}").mock(
            return_value=httpx.Response(
                200,
                json={
                    "audio_type": "breathing",
                    "segments": [
                        {
                            "time_start": 0.0,
                            "time_end": 2.5,
                            "classification": "wheeze",
                            "confidence": 0.85,
                        }
                    ],
                    "summary": "Wheezing detected in expiratory phase",
                    "abnormal_segment_timestamps": [0.5, 1.2],
                    "embedding_id": "emb-audio-001",
                },
            )
        )

        result = await tool.execute(audio_url="http://audio/breathing.wav")
        assert isinstance(result, AudioAnalysisOutput)
        assert result.audio_type == "breathing"
        assert len(result.segments) == 1
        assert result.segments[0].classification == "wheeze"
        assert result.summary == "Wheezing detected in expiratory phase"

    def test_interface_compliance(self, tool):
        assert tool.name == ToolName.AUDIO_ANALYSIS
        assert tool.input_schema["required"] == ["audio_url"]


# ═══════════════════════════════════════════════════════════════
#  HttpHistorySearchTool
# ═══════════════════════════════════════════════════════════════


class TestHttpHistorySearchTool:
    @pytest.fixture
    def tool(self) -> HttpHistorySearchTool:
        return HttpHistorySearchTool(endpoint=MOCK_ENDPOINT, max_retries=0)

    @pytest.mark.asyncio
    @respx.mock
    async def test_successful_history_search(self, tool):
        respx.post(f"{MOCK_ENDPOINT}").mock(
            return_value=httpx.Response(
                200,
                json={
                    "patient_id": "PT-001",
                    "relevant_records": [
                        {
                            "date": "2024-01-15T00:00:00",
                            "record_type": "imaging",
                            "summary": "Prior chest X-ray normal",
                            "similarity_score": 0.88,
                            "clinical_relevance": "Baseline comparison",
                        }
                    ],
                    "timeline_context": "No prior respiratory issues noted",
                },
            )
        )

        result = await tool.execute(patient_id="PT-001", query="prior chest imaging")
        assert isinstance(result, HistorySearchOutput)
        assert result.patient_id == "PT-001"
        assert len(result.relevant_records) == 1
        assert result.relevant_records[0].similarity_score == 0.88
        assert result.timeline_context == "No prior respiratory issues noted"

    def test_uses_search_path(self, tool):
        assert tool._get_path() == "/search"  # HttpHistorySearchTool still overrides (unused in prod)

    def test_interface_compliance(self, tool):
        assert tool.name == ToolName.HISTORY_SEARCH
        assert "patient_id" in tool.input_schema["required"]


# ═══════════════════════════════════════════════════════════════
#  Retry & Error Handling
# ═══════════════════════════════════════════════════════════════


class TestHttpToolResilience:
    @pytest.fixture
    def tool(self) -> HttpImageAnalysisTool:
        return HttpImageAnalysisTool(
            endpoint=MOCK_ENDPOINT, max_retries=1, timeout=2.0
        )

    @pytest.mark.asyncio
    @respx.mock
    async def test_retry_on_server_error(self, tool):
        """500 on first try → success on second try."""
        route = respx.post(f"{MOCK_ENDPOINT}")
        route.side_effect = [
            httpx.Response(500, json={"error": "Internal server error"}),
            httpx.Response(200, json={"modality_detected": "xray", "findings": []}),
        ]

        result = await tool.execute(image_url="http://images/test.png")
        assert isinstance(result, ImageAnalysisOutput)
        assert route.call_count == 2

    @pytest.mark.asyncio
    @respx.mock
    async def test_no_retry_on_client_error(self):
        """400-level errors should not be retried."""
        tool = HttpImageAnalysisTool(endpoint=MOCK_ENDPOINT, max_retries=2)
        route = respx.post(f"{MOCK_ENDPOINT}")
        route.mock(return_value=httpx.Response(400, json={"error": "Bad request"}))

        with pytest.raises(RuntimeError, match="failed after"):
            await tool.execute(image_url="http://images/test.png")

        assert route.call_count == 1  # No retries on 4xx

    @pytest.mark.asyncio
    @respx.mock
    async def test_exhausted_retries_raises(self):
        tool = HttpImageAnalysisTool(endpoint=MOCK_ENDPOINT, max_retries=1)
        respx.post(f"{MOCK_ENDPOINT}").mock(
            return_value=httpx.Response(503, json={"error": "Service unavailable"})
        )

        with pytest.raises(RuntimeError, match="failed after 2 attempts"):
            await tool.execute(image_url="http://images/test.png")


# ═══════════════════════════════════════════════════════════════
#  Factory
# ═══════════════════════════════════════════════════════════════


class TestRegisterHttpTools:
    def test_factory_creates_all_tools(self):
        import os
        os.environ["ANTHROPIC_API_KEY"] = "sk-test"
        settings = Settings(
            anthropic_api_key="sk-test",
            medgemma_4b_endpoint="http://image:8010",
            medgemma_27b_endpoint="http://text:8011",
            hear_endpoint="http://audio:8013",
        )
        tools = register_http_tools(settings)

        assert len(tools) == 4
        assert ToolName.IMAGE_ANALYSIS in tools
        assert ToolName.TEXT_REASONING in tools
        assert ToolName.AUDIO_ANALYSIS in tools
        assert ToolName.HISTORY_SEARCH in tools

        # Verify endpoints are correctly assigned
        assert tools[ToolName.IMAGE_ANALYSIS]._endpoint == "http://image:8010"
        assert tools[ToolName.TEXT_REASONING]._endpoint == "http://text:8011"
        assert tools[ToolName.AUDIO_ANALYSIS]._endpoint == "http://audio:8013"
