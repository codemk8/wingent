"""
OpenRouter provider implementation.

OpenRouter provides access to many models (Claude, GPT, Llama, Mistral, etc.)
through an OpenAI-compatible API at https://openrouter.ai/api/v1.
Useful for accessing cheap models for companion agent tasks.
"""

import os
from typing import List, Dict, Any, Optional
from .base import LLMProvider

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterProvider(LLMProvider):
    """OpenRouter provider — OpenAI-compatible API with access to many models."""

    def __init__(self, api_key: Optional[str] = None):
        try:
            import openai
        except ImportError:
            raise ImportError(
                "openai package not installed. "
                "Install with: pip install openai"
            )

        self.client = openai.OpenAI(
            api_key=api_key or os.environ.get("OPENROUTER_API_KEY", ""),
            base_url=OPENROUTER_BASE_URL,
        )

    async def generate(
        self,
        messages: List[Dict[str, Any]],
        system: str,
        temperature: float,
        max_tokens: int,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        model = kwargs.get("model", "google/gemini-3-flash-preview")

        # Prepend system message (OpenAI-compatible format)
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

        # OpenRouter may not always return usage
        usage = response.usage
        return {
            "content": content,
            "tool_calls": tool_calls,
            "usage": {
                "input_tokens": getattr(usage, "prompt_tokens", 0) if usage else 0,
                "output_tokens": getattr(usage, "completion_tokens", 0) if usage else 0,
                "total_tokens": getattr(usage, "total_tokens", 0) if usage else 0,
            },
            "model": response.model or model,
            "stop_reason": stop_reason,
        }

    def get_available_models(self) -> List[str]:
        from ..config.models import get_models
        return get_models("openrouter")

    def validate_config(self, config: Dict[str, Any]) -> bool:
        temp = config.get("temperature", 0.7)
        if not (0.0 <= temp <= 2.0):
            return False
        max_tokens = config.get("max_tokens", 4096)
        if not (1 <= max_tokens <= 128000):
            return False
        return True
