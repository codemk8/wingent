"""
Abstract base class for LLM providers.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, str]],
        system: str,
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate response from LLM.

        Args:
            messages: List of message dicts with 'role' and 'content'
            system: System prompt/instructions
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters

        Returns:
            Dictionary with:
                - content: str - Generated text
                - usage: dict - Token usage info
                - model: str - Model used
                - stop_reason: str - Why generation stopped
        """
        pass

    @abstractmethod
    def get_available_models(self) -> List[str]:
        """
        Return list of available models for this provider.

        Returns:
            List of model names/IDs
        """
        pass

    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate provider-specific configuration.

        Args:
            config: Configuration dictionary

        Returns:
            True if valid, False otherwise
        """
        pass

    def get_provider_name(self) -> str:
        """
        Get the name of this provider.

        Returns:
            Provider name (e.g., "anthropic", "openai")
        """
        return self.__class__.__name__.lower().replace("provider", "")
