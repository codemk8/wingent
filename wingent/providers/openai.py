"""
OpenAI provider implementation.
"""

from typing import List, Dict, Any, Optional
from .base import LLMProvider


class OpenAIProvider(LLMProvider):
    """OpenAI provider implementation."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key (if None, will use OPENAI_API_KEY env var)
        """
        try:
            import openai
        except ImportError:
            raise ImportError(
                "openai package not installed. "
                "Install with: pip install openai"
            )

        self.client = openai.OpenAI(api_key=api_key)
        self._models = [
            "gpt-4-turbo",
            "gpt-4-turbo-2024-04-09",
            "gpt-4-turbo-preview",
            "gpt-4-0125-preview",
            "gpt-4",
            "gpt-4-0613",
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-0125",
            "gpt-3.5-turbo-1106"
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
        Generate response from OpenAI.

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
        model = kwargs.get("model", "gpt-4-turbo")

        # Prepend system message
        all_messages = [{"role": "system", "content": system}] + messages

        # Call OpenAI API (synchronously - we can make it async later)
        response = self.client.chat.completions.create(
            model=model,
            messages=all_messages,
            temperature=temperature,
            max_tokens=max_tokens
        )

        # Extract response
        content = response.choices[0].message.content or ""
        stop_reason = response.choices[0].finish_reason or "stop"

        return {
            "content": content,
            "usage": {
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            },
            "model": response.model,
            "stop_reason": stop_reason
        }

    def get_available_models(self) -> List[str]:
        """
        Return list of available OpenAI models.

        Returns:
            List of model names
        """
        return self._models.copy()

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate configuration for OpenAI provider.

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
        if not (0.0 <= temp <= 2.0):
            return False

        # Check max_tokens
        max_tokens = config.get("max_tokens", 4096)
        if not (1 <= max_tokens <= 128000):
            return False

        return True
