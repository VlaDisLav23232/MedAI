"""Tool registry — central catalog of available specialist tools.

Implements the Registry pattern: tools register themselves,
orchestrator discovers them at runtime. New tools are added
by implementing BaseTool and calling registry.register().
"""

from __future__ import annotations

import structlog

from medai.domain.entities import ToolName
from medai.domain.interfaces import BaseTool

logger = structlog.get_logger()


class ToolRegistry:
    """Thread-safe registry of specialist tools.

    Usage:
        registry = ToolRegistry()
        registry.register(ImageAnalysisTool())
        tool = registry.get(ToolName.IMAGE_ANALYSIS)
    """

    def __init__(self) -> None:
        self._tools: dict[ToolName, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool. Overwrites if already registered."""
        self._tools[tool.name] = tool
        logger.info("tool_registered", tool_name=tool.name.value)

    def get(self, name: ToolName) -> BaseTool | None:
        """Get a tool by name, or None if not registered."""
        return self._tools.get(name)

    def get_required(self, name: ToolName) -> BaseTool:
        """Get a tool by name, raise if not registered."""
        tool = self._tools.get(name)
        if tool is None:
            raise KeyError(f"Tool '{name.value}' is not registered")
        return tool

    def list_tools(self) -> list[ToolName]:
        """List all registered tool names."""
        return list(self._tools.keys())

    def get_claude_tool_definitions(self) -> list[dict]:
        """Get all tool definitions in Claude API format."""
        return [tool.to_claude_tool_definition() for tool in self._tools.values()]

    def __contains__(self, name: ToolName) -> bool:
        return name in self._tools

    def __len__(self) -> int:
        return len(self._tools)
