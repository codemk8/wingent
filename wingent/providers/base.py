"""
Abstract base class for LLM providers.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, Any]],
        system: str,
        temperature: float,
        max_tokens: int,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate response from LLM.

        Args:
            messages: List of message dicts with 'role' and 'content'.
                      Content may be a string or list of content blocks
                      (for tool results).
            system: System prompt/instructions
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            tools: Optional list of tool schemas for function calling.
                   Each tool dict has 'name', 'description', 'input_schema'.
            **kwargs: Additional provider-specific parameters

        Returns:
            Dictionary with:
                - content: str - Generated text (may be empty if tool_use)
                - tool_calls: list - List of tool call dicts, each with
                    'id', 'name', 'input'. Empty list if no tool calls.
                - usage: dict - Token usage info
                - model: str - Model used
                - stop_reason: str - "end_turn" or "tool_use"
        """
        pass

    @abstractmethod
    def get_available_models(self) -> List[str]:
        """Return list of available models for this provider."""
        pass

    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate provider-specific configuration."""
        pass

    def get_provider_name(self) -> str:
        return self.__class__.__name__.lower().replace("provider", "")
