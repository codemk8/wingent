"""
Anthropic/Claude provider implementation.
"""

from typing import List, Dict, Any, Optional
from .base import LLMProvider


class AnthropicProvider(LLMProvider):
    """Anthropic/Claude provider implementation."""

    def __init__(self, api_key: Optional[str] = None):
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
        messages: List[Dict[str, Any]],
        system: str,
        temperature: float,
        max_tokens: int,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        model = kwargs.get("model", "claude-sonnet-4-5-20250929")

        api_kwargs = dict(
            model=model,
            messages=messages,
            system=system,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if tools:
            api_kwargs["tools"] = tools

        response = self.client.messages.create(**api_kwargs)

        # Parse content blocks
        content = ""
        tool_calls = []
        for block in response.content:
            if hasattr(block, 'text'):
                content += block.text
            elif block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })

        return {
            "content": content,
            "tool_calls": tool_calls,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens
            },
            "model": response.model,
            "stop_reason": response.stop_reason
        }

    def get_available_models(self) -> List[str]:
        return self._models.copy()

    def validate_config(self, config: Dict[str, Any]) -> bool:
        model = config.get("model", "")
        if model and model not in self._models:
            return False
        temp = config.get("temperature", 0.7)
        if not (0.0 <= temp <= 1.0):
            return False
        max_tokens = config.get("max_tokens", 4096)
        if not (1 <= max_tokens <= 100000):
            return False
        return True
