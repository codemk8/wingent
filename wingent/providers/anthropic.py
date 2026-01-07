"""
Anthropic/Claude provider implementation.
"""

from typing import List, Dict, Any, Optional
from .base import LLMProvider


class AnthropicProvider(LLMProvider):
    """Anthropic/Claude provider implementation."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key (if None, will use ANTHROPIC_API_KEY env var)
        """
        try:
            import anthropic
        except ImportError:
            raise ImportError(
                "anthropic package not installed. "
                "Install with: pip install anthropic"
            )

        self.client = anthropic.Anthropic(api_key=api_key)
        self._models = [
            "claude-opus-4-5-20251101",
            "claude-sonnet-4-5-20250929",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307"
        ]

    async def generate(
        self,
        messages: List[Dict[str, str]],
        system: str,
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate response from Claude.

        Args:
            messages: List of message dicts with 'role' and 'content'
            system: System prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters (model, etc.)

        Returns:
            Dictionary with content, usage, model, and stop_reason
        """
        # Get model from kwargs or use default
        model = kwargs.get("model", "claude-sonnet-4-5-20250929")

        # Call Anthropic API (synchronously - we can make it async later)
        response = self.client.messages.create(
            model=model,
            messages=messages,
            system=system,
            temperature=temperature,
            max_tokens=max_tokens
        )

        # Extract text content
        content = ""
        for block in response.content:
            if hasattr(block, 'text'):
                content += block.text

        return {
            "content": content,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens
            },
            "model": response.model,
            "stop_reason": response.stop_reason
        }

    def get_available_models(self) -> List[str]:
        """
        Return list of available Claude models.

        Returns:
            List of model names
        """
        return self._models.copy()

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate configuration for Anthropic provider.

        Args:
            config: Configuration dictionary

        Returns:
            True if valid
        """
        # Check if model is in available models
        model = config.get("model", "")
        if model and model not in self._models:
            return False

        # Check temperature range
        temp = config.get("temperature", 0.7)
        if not (0.0 <= temp <= 1.0):
            return False

        # Check max_tokens
        max_tokens = config.get("max_tokens", 4096)
        if not (1 <= max_tokens <= 100000):
            return False

        return True
