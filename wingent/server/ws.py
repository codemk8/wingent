"""
WebSocket manager for broadcasting real-time execution events to clients.
"""

import json
import asyncio
from typing import Dict, Any, List
from fastapi import WebSocket


class WebSocketManager:
    """Manages WebSocket connections and broadcasts events."""

    def __init__(self):
        self._connections: List[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.append(ws)

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self._connections:
            self._connections.remove(ws)

    async def broadcast(self, event: str, data: Dict[str, Any]) -> None:
        """Send an event to all connected clients."""
        message = json.dumps({"event": event, "data": data})
        dead = []
        for ws in self._connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections.remove(ws)

    def execution_callback(self, event: str, data: Dict[str, Any]) -> None:
        """Callback compatible with TaskExecutor.add_callback().

        Since TaskExecutor callbacks are synchronous, we schedule the
        async broadcast on the running event loop.
        """
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.broadcast(event, data))
        except RuntimeError:
            pass

    @property
    def connection_count(self) -> int:
        return len(self._connections)
