"""
Message data structures and channel implementation.
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional
import asyncio


@dataclass
class Message:
    """Message passed between agents."""
    id: str
    sender_id: str
    recipient_id: str
    content: str
    timestamp: float
    metadata: Dict[str, Any]
    parent_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create from dictionary."""
        return cls(
            id=data["id"],
            sender_id=data["sender_id"],
            recipient_id=data["recipient_id"],
            content=data["content"],
            timestamp=data["timestamp"],
            metadata=data.get("metadata", {}),
            parent_id=data.get("parent_id")
        )


class MessageChannel:
    """Channel for passing messages between agents."""

    def __init__(self, source_id: str, target_id: str, max_queue_size: int = 100):
        """
        Initialize message channel.

        Args:
            source_id: Source agent ID
            target_id: Target agent ID
            max_queue_size: Maximum queue size (default 100)
        """
        self.source_id = source_id
        self.target_id = target_id
        self.queue: asyncio.Queue[Message] = asyncio.Queue(maxsize=max_queue_size)
        self._closed = False

    async def send(self, message: Message):
        """
        Send message through channel.

        Args:
            message: Message to send

        Raises:
            ValueError: If channel is closed or message doesn't match channel
        """
        if self._closed:
            raise ValueError(f"Channel {self.source_id} -> {self.target_id} is closed")

        if message.sender_id != self.source_id:
            raise ValueError(
                f"Message sender {message.sender_id} doesn't match channel source {self.source_id}"
            )

        if message.recipient_id != self.target_id:
            raise ValueError(
                f"Message recipient {message.recipient_id} doesn't match channel target {self.target_id}"
            )

        await self.queue.put(message)

    async def receive(self, timeout: Optional[float] = None) -> Optional[Message]:
        """
        Receive message from channel.

        Args:
            timeout: Optional timeout in seconds

        Returns:
            Message if available, None if timeout

        Raises:
            ValueError: If channel is closed
        """
        if self._closed:
            raise ValueError(f"Channel {self.source_id} -> {self.target_id} is closed")

        try:
            if timeout is not None:
                message = await asyncio.wait_for(self.queue.get(), timeout=timeout)
            else:
                message = await self.queue.get()
            return message
        except asyncio.TimeoutError:
            return None

    def close(self):
        """Close the channel."""
        self._closed = True

    def is_closed(self) -> bool:
        """Check if channel is closed."""
        return self._closed

    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return self.queue.empty()

    def qsize(self) -> int:
        """Get current queue size."""
        return self.queue.qsize()

    def __repr__(self) -> str:
        """String representation."""
        status = "closed" if self._closed else f"open, {self.qsize()} messages"
        return f"MessageChannel({self.source_id} -> {self.target_id}, {status})"
