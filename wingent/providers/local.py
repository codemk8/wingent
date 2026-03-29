"""
Local model provider implementation (Ollama).
"""

from typing import List, Dict, Any, Optional
from .base import LLMProvider


class LocalProvider(LLMProvider):
    """Local model provider using Ollama."""

    def __init__(self, host: str = "http://localhost:11434"):
        self.host = host
        self._models = [
            "llama3",
            "llama3:70b",
            "llama3:8b",
            "mistral",
            "mistral:7b",
            "codellama",
            "codellama:13b",
            "codellama:34b",
            "gemma:7b",
            "phi3",
            "phi3:mini"
        ]

        try:
            import ollama
            self.client = ollama.Client(host=host)
        except ImportError:
            print("Warning: ollama package not installed. Install with: pip install ollama")
            self.client = None

    async def generate(
        self,
        messages: List[Dict[str, Any]],
        system: str,
        temperature: float,
        max_tokens: int,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        if self.client is None:
            raise RuntimeError("Ollama client not available. Install with: pip install ollama")

        if tools:
            print("Warning: Tool use is not supported by local Ollama provider. Tools will be ignored.")

        model = kwargs.get("model", "llama3")

        # Prepend system message
        all_messages = [{"role": "system", "content": system}] + messages

        try:
            response = self.client.chat(
                model=model,
                messages=all_messages,
                options={
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            )

            content = response.get("message", {}).get("content", "")

            # Rough token estimate: ~4 chars per token
            estimated_input_tokens = sum(len(msg.get("content", "")) for msg in all_messages) // 4
            estimated_output_tokens = len(content) // 4

            return {
                "content": content,
                "tool_calls": [],
                "usage": {
                    "input_tokens": estimated_input_tokens,
                    "output_tokens": estimated_output_tokens,
                    "total_tokens": estimated_input_tokens + estimated_output_tokens
                },
                "model": model,
                "stop_reason": "end_turn"
            }

        except Exception as e:
            raise RuntimeError(f"Ollama API error: {e}")

    def get_available_models(self) -> List[str]:
        if self.client:
            try:
                models = self.client.list()
                return [model["name"] for model in models.get("models", [])]
            except Exception:
                pass
        return self._models.copy()

    def validate_config(self, config: Dict[str, Any]) -> bool:
        temp = config.get("temperature", 0.7)
        if not (0.0 <= temp <= 2.0):
            return False
        max_tokens = config.get("max_tokens", 4096)
        if not (1 <= max_tokens <= 100000):
            return False
        return True
