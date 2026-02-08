"""Unit tests for tool registry and mock tools.

Validates the Registry pattern, tool interface compliance,
and mock tool output structure.
"""

from __future__ import annotations

import pytest

from medai.domain.entities import (
    ImageAnalysisOutput,
    TextReasoningOutput,
    AudioAnalysisOutput,
    HistorySearchOutput,
    ToolName,
)
from medai.domain.interfaces import BaseTool
from medai.services.tool_registry import ToolRegistry
from medai.tools.mock import (
    MockImageAnalysisTool,
    MockTextReasoningTool,
    MockAudioAnalysisTool,
    MockHistorySearchTool,
    register_mock_tools,
)


# ═══════════════════════════════════════════════════════════════
#  ToolRegistry Tests
# ═══════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestToolRegistry:
    def test_register_and_get(self):
        registry = ToolRegistry()
        tool = MockImageAnalysisTool()
        registry.register(tool)

        assert ToolName.IMAGE_ANALYSIS in registry
        assert registry.get(ToolName.IMAGE_ANALYSIS) is tool

    def test_get_nonexistent(self):
        registry = ToolRegistry()
        assert registry.get(ToolName.IMAGE_ANALYSIS) is None

    def test_get_required_raises(self):
        registry = ToolRegistry()
        with pytest.raises(KeyError, match="image_analysis"):
            registry.get_required(ToolName.IMAGE_ANALYSIS)

    def test_list_tools(self):
        registry = ToolRegistry()
        tools = register_mock_tools()
        for tool in tools.values():
            registry.register(tool)

        listed = registry.list_tools()
        assert ToolName.IMAGE_ANALYSIS in listed
        assert ToolName.TEXT_REASONING in listed
        assert ToolName.AUDIO_ANALYSIS in listed
        assert ToolName.HISTORY_SEARCH in listed
        assert ToolName.IMAGE_EXPLAINABILITY in listed
        assert len(listed) == 5

    def test_len(self):
        registry = ToolRegistry()
        assert len(registry) == 0
        registry.register(MockImageAnalysisTool())
        assert len(registry) == 1

    def test_claude_tool_definitions(self):
        registry = ToolRegistry()
        registry.register(MockImageAnalysisTool())
        registry.register(MockTextReasoningTool())

        defs = registry.get_claude_tool_definitions()
        assert len(defs) == 2

        for d in defs:
            assert "name" in d
            assert "description" in d
            assert "input_schema" in d
            assert d["input_schema"]["type"] == "object"
            assert "properties" in d["input_schema"]


# ═══════════════════════════════════════════════════════════════
#  Mock Tool Interface Compliance
# ═══════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestMockToolsInterface:
    """Verify all mock tools implement the BaseTool interface correctly."""

    @pytest.mark.parametrize("tool_class,expected_name", [
        (MockImageAnalysisTool, ToolName.IMAGE_ANALYSIS),
        (MockTextReasoningTool, ToolName.TEXT_REASONING),
        (MockAudioAnalysisTool, ToolName.AUDIO_ANALYSIS),
        (MockHistorySearchTool, ToolName.HISTORY_SEARCH),
    ])
    def test_tool_is_base_tool(self, tool_class, expected_name):
        tool = tool_class()
        assert isinstance(tool, BaseTool)
        assert tool.name == expected_name
        assert isinstance(tool.description, str)
        assert len(tool.description) > 10  # meaningful description

    @pytest.mark.parametrize("tool_class", [
        MockImageAnalysisTool,
        MockTextReasoningTool,
        MockAudioAnalysisTool,
        MockHistorySearchTool,
    ])
    def test_tool_input_schema_valid(self, tool_class):
        tool = tool_class()
        schema = tool.input_schema
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "required" in schema
        assert isinstance(schema["required"], list)

    @pytest.mark.parametrize("tool_class", [
        MockImageAnalysisTool,
        MockTextReasoningTool,
        MockAudioAnalysisTool,
        MockHistorySearchTool,
    ])
    def test_tool_claude_definition(self, tool_class):
        tool = tool_class()
        defn = tool.to_claude_tool_definition()
        assert defn["name"] == tool.name.value
        assert defn["description"] == tool.description
        assert defn["input_schema"] == tool.input_schema


# ═══════════════════════════════════════════════════════════════
#  Mock Tool Execution Tests
# ═══════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestMockToolExecution:
    @pytest.mark.asyncio
    async def test_image_analysis_output(self):
        tool = MockImageAnalysisTool()
        output = await tool.execute(image_url="test.png")

        assert isinstance(output, ImageAnalysisOutput)
        assert output.tool == ToolName.IMAGE_ANALYSIS
        assert len(output.findings) > 0
        assert all(0 <= f.confidence <= 1 for f in output.findings)
        assert output.attention_heatmap_url is not None

        # JSON serialization
        data = output.model_dump()
        assert "findings" in data
        ImageAnalysisOutput.model_validate(data)

    @pytest.mark.asyncio
    async def test_text_reasoning_output(self):
        tool = MockTextReasoningTool()
        output = await tool.execute(clinical_context="test")

        assert isinstance(output, TextReasoningOutput)
        assert output.tool == ToolName.TEXT_REASONING
        assert len(output.reasoning_chain) > 0
        assert 0 <= output.confidence <= 1
        assert output.assessment != ""

    @pytest.mark.asyncio
    async def test_audio_analysis_output(self):
        tool = MockAudioAnalysisTool()
        output = await tool.execute(audio_url="test.wav")

        assert isinstance(output, AudioAnalysisOutput)
        assert output.tool == ToolName.AUDIO_ANALYSIS
        assert len(output.segments) > 0
        assert all(0 <= s.confidence <= 1 for s in output.segments)

    @pytest.mark.asyncio
    async def test_history_search_output(self):
        tool = MockHistorySearchTool()
        output = await tool.execute(patient_id="PT-TEST", query="respiratory history")

        assert isinstance(output, HistorySearchOutput)
        assert output.patient_id == "PT-TEST"
        assert len(output.relevant_records) > 0
        assert output.timeline_context != ""
