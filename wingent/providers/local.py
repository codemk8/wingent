"""
Local model provider implementation (Ollama).
"""

from typing import List, Dict, Any, Optional
from .base import LLMProvider


class LocalProvider(LLMProvider):
    """Local model provider using Ollama."""

    def __init__(self, host: str = "http://localhost:11434"):
        """
        Initialize Local provider.

        Args:
            host: Ollama server host (default: http://localhost:11434)
        """
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

        # Try to import ollama
        try:
            import ollama
            self.client = ollama.Client(host=host)
        except ImportError:
            print("Warning: ollama package not installed. Install with: pip install ollama")
            self.client = None

    async def generate(
        self,
        messages: List[Dict[str, str]],
        system: str,
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate response from local model.

        Args:
            messages: List of message dicts with 'role' and 'content'
            system: System prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters (model, etc.)

        Returns:
            Dictionary with content, usage, model, and stop_reason
        """
        if self.client is None:
            raise RuntimeError("Ollama client not available. Install with: pip install ollama")

        # Get model from kwargs or use default
        model = kwargs.get("model", "llama3")

        # Prepend system message
        all_messages = [{"role": "system", "content": system}] + messages

        # Call Ollama API
        try:
            response = self.client.chat(
                model=model,
                messages=all_messages,
                options={
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            )

            # Extract response
            content = response.get("message", {}).get("content", "")

            # Ollama doesn't provide token counts by default, estimate
            # This is a rough estimate: ~4 chars per token
            estimated_input_tokens = sum(len(msg.get("content", "")) for msg in all_messages) // 4
            estimated_output_tokens = len(content) // 4

            return {
                "content": content,
                "usage": {
                    "input_tokens": estimated_input_tokens,
                    "output_tokens": estimated_output_tokens,
                    "total_tokens": estimated_input_tokens + estimated_output_tokens
                },
                "model": model,
                "stop_reason": "stop"
            }

        except Exception as e:
            raise RuntimeError(f"Ollama API error: {e}")

    def get_available_models(self) -> List[str]:
        """
        Return list of available local models.

        Returns:
            List of model names
        """
        if self.client:
            try:
                # Try to get actual list from Ollama
                models = self.client.list()
                return [model["name"] for model in models.get("models", [])]
            except Exception:
                pass

        # Fall back to default list
        return self._models.copy()

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate configuration for local provider.

        Args:
            config: Configuration dictionary

        Returns:
            True if valid
        """
        # Check temperature range
        temp = config.get("temperature", 0.7)
        if not (0.0 <= temp <= 2.0):
            return False

        # Check max_tokens
        max_tokens = config.get("max_tokens", 4096)
        if not (1 <= max_tokens <= 100000):
            return False

        return True
