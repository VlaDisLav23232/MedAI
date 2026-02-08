"""Unit tests for SigLIP-based image explainability tool.

Tests cover:
- HttpSigLipTool: payload construction (taxonomy + overrides), response parsing,
  heatmap extraction, embedding handling, inference metadata
- MockImageExplainabilityTool: output contract compliance
- Taxonomy loading and validation
- Entity serialization round-trips
- Factory registration
"""

from __future__ import annotations

import json

import pytest
import httpx
import respx

from medai.domain.entities import (
    ConditionScore,
    ConfidenceMethod,
    ImageExplainabilityOutput,
    InferenceMetadata,
    Modality,
    ToolName,
)
from medai.tools.http import HttpSigLipTool, _load_taxonomy, register_http_tools
from medai.tools.mock import MockImageExplainabilityTool, register_mock_tools
from medai.config import Settings


MOCK_ENDPOINT = "http://mock-siglip:8012"


# ═══════════════════════════════════════════════════════════════
#  Taxonomy Loading
# ═══════════════════════════════════════════════════════════════


class TestTaxonomy:
    def test_taxonomy_loads_all_modalities(self):
        """All 11 Modality enum values must be present."""
        import medai.tools.http as http_module
        http_module._taxonomy_cache = None  # Reset cache for test isolation

        taxonomy = _load_taxonomy()
        expected = [m.value for m in Modality]
        for modality in expected:
            assert modality in taxonomy, f"Missing modality: {modality}"
            assert len(taxonomy[modality]) > 0, f"Empty labels for: {modality}"

    def test_taxonomy_no_empty_labels(self):
        """No label should be an empty string."""
        import medai.tools.http as http_module
        http_module._taxonomy_cache = None

        taxonomy = _load_taxonomy()
        for modality, labels in taxonomy.items():
            for label in labels:
                assert label.strip(), f"Empty label in {modality}"

    def test_taxonomy_json_valid(self, tmp_path):
        """Custom taxonomy path should be loadable."""
        import medai.tools.http as http_module
        http_module._taxonomy_cache = None

        custom = {"xray": ["test condition"], "other": ["fallback"]}
        p = tmp_path / "custom_taxonomy.json"
        p.write_text(json.dumps(custom))

        taxonomy = _load_taxonomy(str(p))
        assert taxonomy["xray"] == ["test condition"]

        # Reset
        http_module._taxonomy_cache = None


# ═══════════════════════════════════════════════════════════════
#  HttpSigLipTool — Interface Compliance
# ═══════════════════════════════════════════════════════════════


class TestHttpSigLipToolInterface:
    @pytest.fixture
    def tool(self) -> HttpSigLipTool:
        return HttpSigLipTool(endpoint=MOCK_ENDPOINT, max_retries=0)

    def test_name(self, tool):
        assert tool.name == ToolName.IMAGE_EXPLAINABILITY

    def test_description_mentions_explainability(self, tool):
        assert "explainability" in tool.description.lower()
        assert "heatmap" in tool.description.lower()

    def test_input_schema(self, tool):
        schema = tool.input_schema
        assert schema["required"] == ["image_url"]
        assert "image_url" in schema["properties"]
        assert "modality_hint" in schema["properties"]
        assert "condition_labels" in schema["properties"]
        assert schema["properties"]["condition_labels"]["type"] == "array"

    def test_claude_tool_definition(self, tool):
        defn = tool.to_claude_tool_definition()
        assert defn["name"] == "image_explainability"
        assert defn["strict"] is True
        assert "input_schema" in defn


# ═══════════════════════════════════════════════════════════════
#  HttpSigLipTool — Payload Construction
# ═══════════════════════════════════════════════════════════════


class TestHttpSigLipToolPayload:
    @pytest.fixture
    def tool(self) -> HttpSigLipTool:
        return HttpSigLipTool(endpoint=MOCK_ENDPOINT, max_retries=0)

    def test_payload_uses_taxonomy_defaults(self, tool):
        """When no condition_labels provided, uses taxonomy for modality."""
        payload = tool._build_request_payload(
            image_url="http://img/chest.png",
            modality_hint="xray",
        )
        assert payload["image_url"] == "http://img/chest.png"
        assert payload["modality_hint"] == "xray"
        assert len(payload["condition_labels"]) >= 8  # xray has 12 labels
        assert "consolidation consistent with pneumonia" in payload["condition_labels"]

    def test_payload_custom_labels_override(self, tool):
        """Request-provided labels override taxonomy defaults."""
        payload = tool._build_request_payload(
            image_url="http://img/custom.png",
            modality_hint="xray",
            condition_labels=["custom A", "custom B"],
        )
        assert payload["condition_labels"] == ["custom A", "custom B"]

    def test_payload_empty_labels_uses_taxonomy(self, tool):
        """Empty list should still use taxonomy defaults."""
        payload = tool._build_request_payload(
            image_url="http://img/test.png",
            modality_hint="ct",
            condition_labels=[],
        )
        assert len(payload["condition_labels"]) >= 5  # ct taxonomy has labels

    def test_payload_unknown_modality_uses_other(self, tool):
        """Unknown modality falls back to 'other' taxonomy."""
        payload = tool._build_request_payload(
            image_url="http://img/test.png",
            modality_hint="quantum_imaging",
        )
        # Should use "other" taxonomy as fallback
        assert len(payload["condition_labels"]) > 0

    def test_payload_includes_embedding_request(self, tool):
        """Payload should request embeddings."""
        payload = tool._build_request_payload(image_url="http://img/test.png")
        assert payload["return_embedding"] is True


# ═══════════════════════════════════════════════════════════════
#  HttpSigLipTool — Response Parsing
# ═══════════════════════════════════════════════════════════════


class TestHttpSigLipToolParsing:
    @pytest.fixture
    def tool(self) -> HttpSigLipTool:
        return HttpSigLipTool(endpoint=MOCK_ENDPOINT, max_retries=0)

    def test_parse_full_response(self, tool):
        """Parse a complete SigLIP response with scores, heatmaps, embedding."""
        data = {
            "scores": [
                {"label": "pneumonia consolidation", "probability": 0.82,
                 "sigmoid_score": 3.2e-05, "raw_logit": -10.35},
                {"label": "pleural effusion", "probability": 0.45,
                 "sigmoid_score": 1.7e-05, "raw_logit": -10.98},
                {"label": "normal lungs", "probability": 0.12,
                 "sigmoid_score": 4.6e-06, "raw_logit": -12.29},
            ],
            "heatmaps": [
                {"label": "pneumonia consolidation", "heatmap_base64": "iVBORw0KGgo="},
                {"label": "pleural effusion", "heatmap_base64": "AAABBB123="},
            ],
            "image_embedding": [0.01, -0.02, 0.03],
            "inference_time_ms": 142.3,
            "model_id": "google/medsiglip-448",
            "modality_hint": "xray",
        }

        result = tool._parse_response(data)

        assert isinstance(result, ImageExplainabilityOutput)
        assert result.tool == "image_explainability"
        assert result.modality_detected == Modality.XRAY
        assert len(result.condition_scores) == 3
        assert result.condition_scores[0].label == "pneumonia consolidation"
        assert result.condition_scores[0].probability == 0.82
        assert result.condition_scores[0].sigmoid_score == 3.2e-05
        assert result.condition_scores[0].raw_logit == -10.35
        # Heatmap data URI should be prepended with data:image/png;base64,
        assert result.condition_scores[0].heatmap_data_uri == "data:image/png;base64,iVBORw0KGgo="
        # Third score has no heatmap
        assert result.condition_scores[2].heatmap_data_uri is None

    def test_top_scoring_heatmap_in_attention_url(self, tool):
        """attention_heatmap_url should be the top-scoring condition's heatmap."""
        data = {
            "scores": [
                {"label": "condition_a", "probability": 0.3},
                {"label": "condition_b", "probability": 0.9},
            ],
            "heatmaps": [
                {"label": "condition_b", "heatmap_base64": "topHeatmapB64="},
            ],
            "model_id": "google/medsiglip-448",
            "inference_time_ms": 100,
        }
        result = tool._parse_response(data)
        assert result.attention_heatmap_url == "data:image/png;base64,topHeatmapB64="

    def test_parse_with_embedding(self, tool):
        """Image embedding should be preserved."""
        data = {
            "scores": [{"label": "test", "probability": 0.5}],
            "heatmaps": [],
            "image_embedding": [0.1, 0.2, 0.3, 0.4],
            "model_id": "siglip",
            "inference_time_ms": 50,
        }
        result = tool._parse_response(data)
        assert result.embedding == [0.1, 0.2, 0.3, 0.4]

    def test_parse_without_embedding(self, tool):
        """Null embedding should be handled gracefully."""
        data = {
            "scores": [{"label": "test", "probability": 0.5}],
            "heatmaps": [],
            "image_embedding": None,
            "model_id": "siglip",
            "inference_time_ms": 50,
        }
        result = tool._parse_response(data)
        assert result.embedding is None

    def test_parse_inference_metadata(self, tool):
        """Inference metadata should be extracted."""
        data = {
            "scores": [],
            "heatmaps": [],
            "model_id": "google/medsiglip-448",
            "inference_time_ms": 142.3,
        }
        result = tool._parse_response(data)
        assert result.inference is not None
        assert result.inference.model_id == "google/medsiglip-448"
        assert result.inference.temperature == 0.0  # deterministic
        assert result.inference.token_count == 0  # not generative
        assert result.inference.inference_time_ms == 142.3

    def test_parse_empty_scores(self, tool):
        """Empty scores list should not crash."""
        data = {
            "scores": [],
            "heatmaps": [],
            "model_id": "siglip",
            "inference_time_ms": 10,
        }
        result = tool._parse_response(data)
        assert result.condition_scores == []
        assert result.attention_heatmap_url is None


# ═══════════════════════════════════════════════════════════════
#  HttpSigLipTool — HTTP Integration (respx-mocked)
# ═══════════════════════════════════════════════════════════════


class TestHttpSigLipToolExecution:
    @pytest.fixture
    def tool(self) -> HttpSigLipTool:
        return HttpSigLipTool(endpoint=MOCK_ENDPOINT, max_retries=0)

    @pytest.mark.asyncio
    @respx.mock
    async def test_successful_execution(self, tool):
        """Full round-trip: build payload → HTTP POST → parse response."""
        respx.post(f"{MOCK_ENDPOINT}").mock(
            return_value=httpx.Response(
                200,
                json={
                    "scores": [
                        {"label": "consolidation consistent with pneumonia", "probability": 0.78},
                        {"label": "normal lung fields", "probability": 0.15},
                    ],
                    "heatmaps": [
                        {"label": "consolidation consistent with pneumonia", "heatmap_base64": "abc123"},
                    ],
                    "image_embedding": [0.1, -0.2],
                    "inference_time_ms": 150.0,
                    "model_id": "google/medsiglip-448",
                    "modality_hint": "xray",
                },
            )
        )

        result = await tool.execute(
            image_url="http://images/chest.png",
            modality_hint="xray",
        )

        assert isinstance(result, ImageExplainabilityOutput)
        assert result.modality_detected == Modality.XRAY
        assert len(result.condition_scores) == 2
        assert result.condition_scores[0].probability == 0.78
        assert result.attention_heatmap_url is not None
        assert result.embedding is not None

    @pytest.mark.asyncio
    @respx.mock
    async def test_server_error_raises(self, tool):
        """500 with no retries should raise RuntimeError."""
        respx.post(f"{MOCK_ENDPOINT}").mock(
            return_value=httpx.Response(500, json={"error": "GPU OOM"})
        )

        with pytest.raises(RuntimeError, match="failed after"):
            await tool.execute(image_url="http://images/test.png")


# ═══════════════════════════════════════════════════════════════
#  MockImageExplainabilityTool
# ═══════════════════════════════════════════════════════════════


class TestMockImageExplainabilityTool:
    @pytest.fixture
    def tool(self) -> MockImageExplainabilityTool:
        return MockImageExplainabilityTool()

    def test_interface_compliance(self, tool):
        assert tool.name == ToolName.IMAGE_EXPLAINABILITY
        assert "explainability" in tool.description.lower()
        schema = tool.input_schema
        assert schema["required"] == ["image_url"]

    @pytest.mark.asyncio
    async def test_execute_returns_valid_output(self, tool):
        result = await tool.execute(image_url="http://test.png")
        assert isinstance(result, ImageExplainabilityOutput)
        assert result.tool == "image_explainability"
        assert result.modality_detected == Modality.XRAY
        assert len(result.condition_scores) >= 3
        assert result.attention_heatmap_url is not None
        assert result.embedding is not None
        assert result.inference is not None
        assert result.inference.model_id == "google/medsiglip-448"

    @pytest.mark.asyncio
    async def test_probabilities_in_valid_range(self, tool):
        """All probabilities must be in [0, 1]."""
        result = await tool.execute(image_url="http://test.png")
        for score in result.condition_scores:
            assert 0.0 <= score.probability <= 1.0, f"Out of range: {score.probability}"

    @pytest.mark.asyncio
    async def test_scores_have_realistic_distribution(self, tool):
        """Not all scores should be the same — mock should be realistic."""
        result = await tool.execute(image_url="http://test.png")
        probs = [s.probability for s in result.condition_scores]
        assert len(set(probs)) > 1, "All probabilities are identical"

    def test_claude_tool_definition(self, tool):
        defn = tool.to_claude_tool_definition()
        assert defn["name"] == "image_explainability"
        assert defn["strict"] is True


# ═══════════════════════════════════════════════════════════════
#  Entity Serialization
# ═══════════════════════════════════════════════════════════════


class TestEntitySerialization:
    def test_condition_score_round_trip(self):
        cs = ConditionScore(
            label="pneumonia",
            probability=0.82,
            heatmap_data_uri="data:image/png;base64,abc",
        )
        d = cs.model_dump()
        cs2 = ConditionScore.model_validate(d)
        assert cs2 == cs

    def test_condition_score_json_round_trip(self):
        cs = ConditionScore(label="test", probability=0.5)
        j = cs.model_dump_json()
        cs2 = ConditionScore.model_validate_json(j)
        assert cs2.label == "test"
        assert cs2.probability == 0.5
        assert cs2.heatmap_data_uri is None

    def test_explainability_output_round_trip(self):
        output = ImageExplainabilityOutput(
            modality_detected=Modality.CT,
            condition_scores=[
                ConditionScore(label="mass", probability=0.7),
            ],
            attention_heatmap_url="data:image/png;base64,xyz",
            embedding=[0.1, 0.2],
            inference=InferenceMetadata(
                model_id="siglip",
                temperature=0.0,
                token_count=0,
                inference_time_ms=100,
            ),
        )
        d = output.model_dump()
        output2 = ImageExplainabilityOutput.model_validate(d)
        assert output2.modality_detected == Modality.CT
        assert output2.condition_scores[0].probability == 0.7
        assert output2.inference.model_id == "siglip"

    def test_confidence_method_siglip(self):
        assert ConfidenceMethod.SIGLIP_PATCH_SIMILARITY.value == "siglip_patch_similarity"


# ═══════════════════════════════════════════════════════════════
#  Factory Registration
# ═══════════════════════════════════════════════════════════════


class TestFactoryRegistration:
    def test_mock_factory_includes_explainability(self):
        tools = register_mock_tools()
        assert ToolName.IMAGE_EXPLAINABILITY in tools
        assert len(tools) == 5  # 4 original + 1 new

    def test_http_factory_includes_explainability(self):
        settings = Settings(
            anthropic_api_key="sk-test",
            medgemma_4b_endpoint="http://img:8010",
            medgemma_27b_endpoint="http://txt:8011",
            hear_endpoint="http://aud:8013",
            medsiglip_endpoint="http://siglip:8012",
        )
        tools = register_http_tools(settings)
        assert ToolName.IMAGE_EXPLAINABILITY in tools
        assert len(tools) == 5
        assert tools[ToolName.IMAGE_EXPLAINABILITY]._endpoint == "http://siglip:8012"
