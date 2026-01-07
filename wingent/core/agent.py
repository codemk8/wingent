"""
Agent configuration and runtime classes.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, List
import time


@dataclass
class VisualPosition:
    """Visual position on canvas."""
    x: int
    y: int

    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary."""
        return {"x": self.x, "y": self.y}

    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> 'VisualPosition':
        """Create from dictionary."""
        return cls(x=data["x"], y=data["y"])


@dataclass
class AgentConfig:
    """Configuration for a single agent."""
    id: str
    name: str
    provider: str  # "anthropic", "openai", "local"
    model: str  # e.g., "claude-sonnet-4-5-20250929"
    system_prompt: str
    temperature: float = 0.7
    max_tokens: int = 4096
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        if data["metadata"] is None:
            data["metadata"] = {}
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentConfig':
        """Create from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            provider=data["provider"],
            model=data["model"],
            system_prompt=data["system_prompt"],
            temperature=data.get("temperature", 0.7),
            max_tokens=data.get("max_tokens", 4096),
            metadata=data.get("metadata")
        )


class Agent:
    """Runtime agent instance."""

    def __init__(self, config: AgentConfig, provider: 'LLMProvider'):
        """
        Initialize agent.

        Args:
            config: Agent configuration
            provider: LLM provider instance
        """
        self.config = config
        self.provider = provider
        self.message_history: List['Message'] = []

    async def process_message(self, message: 'Message') -> 'Message':
        """
        Process incoming message and generate response.

        Args:
            message: Incoming message

        Returns:
            Response message
        """
        from .message import Message
        import uuid

        # Add to history
        self.message_history.append(message)

        # Format messages for LLM
        formatted_messages = [
            {"role": "user", "content": msg.content}
            for msg in self.message_history
        ]

        # Generate response
        response = await self.provider.generate(
            messages=formatted_messages,
            system=self.config.system_prompt,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            model=self.config.model
        )

        # Create response message
        response_msg = Message(
            id=str(uuid.uuid4()),
            sender_id=self.config.id,
            recipient_id=message.sender_id,  # Reply to sender
            content=response["content"],
            timestamp=time.time(),
            metadata={
                "usage": response.get("usage", {}),
                "model": response.get("model", self.config.model),
                "stop_reason": response.get("stop_reason", "")
            },
            parent_id=message.id
        )

        # Add response to history (as assistant message)
        self.message_history.append(response_msg)

        return response_msg

    def add_to_history(self, message: 'Message'):
        """
        Add message to agent's conversation history.

        Args:
            message: Message to add
        """
        self.message_history.append(message)

    def clear_history(self):
        """Clear conversation history."""
        self.message_history.clear()
