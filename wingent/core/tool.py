"""
Tool abstraction for agent capabilities.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ToolParameter:
    """Definition of a single tool parameter."""
    name: str
    type: str  # "string", "integer", "boolean", "number", "object", "array"
    description: str
    required: bool = True
    enum: Optional[List[str]] = None
    default: Optional[Any] = None


@dataclass
class ToolDefinition:
    """Schema that gets sent to the LLM for function calling."""
    name: str
    description: str
    parameters: List[ToolParameter] = field(default_factory=list)

    def to_llm_schema(self) -> Dict[str, Any]:
        """Convert to the JSON Schema format expected by LLM providers."""
        properties = {}
        required = []
        for p in self.parameters:
            prop: Dict[str, Any] = {"type": p.type, "description": p.description}
            if p.enum:
                prop["enum"] = p.enum
            if p.default is not None:
                prop["default"] = p.default
            properties[p.name] = prop
            if p.required:
                required.append(p.name)
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": properties,
                "required": required,
            }
        }


class Tool(ABC):
    """Base class for tools that agents can use."""

    @abstractmethod
    def definition(self) -> ToolDefinition:
        """Return the tool's schema for the LLM."""
        ...

    @abstractmethod
    async def execute(self, **kwargs) -> str:
        """Execute the tool and return a string result."""
        ...


class ToolRegistry:
    """Collection of tools available to an agent."""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        defn = tool.definition()
        self._tools[defn.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def list_definitions(self) -> List[ToolDefinition]:
        return [t.definition() for t in self._tools.values()]

    def to_llm_tools(self) -> List[Dict[str, Any]]:
        return [d.to_llm_schema() for d in self.list_definitions()]

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools
