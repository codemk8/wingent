"""
OpenAI provider implementation.
"""

from typing import List, Dict, Any, Optional
from .base import LLMProvider


class OpenAIProvider(LLMProvider):
    """OpenAI provider implementation."""

    def __init__(self, api_key: Optional[str] = None):
        try:
            import openai
        except ImportError:
            raise ImportError(
                "openai package not installed. "
                "Install with: pip install openai"
            )

        self.client = openai.OpenAI(api_key=api_key)
        from ..config.models import get_models
        self._models = get_models("openai")

    async def generate(
        self,
        messages: List[Dict[str, Any]],
        system: str,
        temperature: float,
        max_tokens: int,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        model = kwargs.get("model", "gpt-4.1")

        # Prepend system message
        all_messages = [{"role": "system", "content": system}] + messages

        api_kwargs = dict(
            model=model,
            messages=all_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # Convert tool schemas from Anthropic format to OpenAI format
        if tools:
            openai_tools = []
            for t in tools:
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": t["name"],
                        "description": t.get("description", ""),
                        "parameters": t.get("input_schema", {}),
                    }
                })
            api_kwargs["tools"] = openai_tools

        response = self.client.chat.completions.create(**api_kwargs)

        choice = response.choices[0]
        content = choice.message.content or ""
        stop_reason = choice.finish_reason or "stop"

        # Parse tool calls
        tool_calls = []
        if choice.message.tool_calls:
            import json
            for tc in choice.message.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "input": json.loads(tc.function.arguments),
                })
            stop_reason = "tool_use"

        return {
            "content": content,
            "tool_calls": tool_calls,
            "usage": {
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            },
            "model": response.model,
            "stop_reason": stop_reason
        }

    def get_available_models(self) -> List[str]:
        return self._models.copy()

    def validate_config(self, config: Dict[str, Any]) -> bool:
        model = config.get("model", "")
        if model and model not in self._models:
            return False
        temp = config.get("temperature", 0.7)
        if not (0.0 <= temp <= 2.0):
            return False
        max_tokens = config.get("max_tokens", 4096)
        if not (1 <= max_tokens <= 128000):
            return False
        return True
