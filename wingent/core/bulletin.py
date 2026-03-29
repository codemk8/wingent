"""
Bulletin board for agent coordination within a task scope.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum
import asyncio
import uuid
import time


class PostType(Enum):
    STATUS_UPDATE = "status_update"
    WORK_ITEM = "work_item"
    CLAIM = "claim"
    QUESTION = "question"
    ANSWER = "answer"
    RESULT = "result"
    DIRECTIVE = "directive"


@dataclass
class BulletinPost:
    """A single post on the bulletin board."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    author_id: str = ""
    post_type: PostType = PostType.STATUS_UPDATE
    content: str = ""
    references_post_id: Optional[str] = None
    references_task_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "author_id": self.author_id,
            "post_type": self.post_type.value,
            "content": self.content,
            "references_post_id": self.references_post_id,
            "references_task_id": self.references_task_id,
            "timestamp": self.timestamp,
            "metadata": self.metadata.copy(),
        }


class BulletinBoard:
    """Shared coordination space for a task scope.

    Each decomposed task gets its own board. The manager and all
    subagents share this board for posting updates, claiming work,
    asking questions, and reporting results.
    """

    def __init__(self, task_id: str):
        self.task_id = task_id
        self._posts: List[BulletinPost] = []
        self._subscribers: Dict[str, asyncio.Queue] = {}
        self._lock: asyncio.Lock = asyncio.Lock()

    async def post(self, post: BulletinPost) -> None:
        async with self._lock:
            self._posts.append(post)
            for agent_id, queue in self._subscribers.items():
                if agent_id != post.author_id:
                    await queue.put(post)

    def subscribe(self, agent_id: str) -> None:
        if agent_id not in self._subscribers:
            self._subscribers[agent_id] = asyncio.Queue()

    async def wait_for_post(self, agent_id: str, timeout: Optional[float] = None) -> Optional[BulletinPost]:
        queue = self._subscribers.get(agent_id)
        if not queue:
            return None
        try:
            if timeout:
                return await asyncio.wait_for(queue.get(), timeout=timeout)
            return await queue.get()
        except asyncio.TimeoutError:
            return None

    def get_posts(self, post_type: Optional[PostType] = None,
                  since: Optional[float] = None,
                  limit: Optional[int] = None) -> List[BulletinPost]:
        posts = self._posts
        if post_type:
            posts = [p for p in posts if p.post_type == post_type]
        if since:
            posts = [p for p in posts if p.timestamp > since]
        if limit:
            posts = posts[-limit:]
        return posts

    def get_summary(self) -> str:
        """Human-readable summary for injecting into LLM context."""
        if not self._posts:
            return "Bulletin board is empty."

        lines = [f"Bulletin Board (task {self.task_id[:8]}...) - {len(self._posts)} posts:"]
        for post in self._posts[-10:]:  # Last 10 posts
            ts = time.strftime("%H:%M:%S", time.localtime(post.timestamp))
            ref = ""
            if post.references_task_id:
                ref = f" [task:{post.references_task_id[:8]}]"
            lines.append(f"  [{ts}] {post.author_id[:12]}: [{post.post_type.value}]{ref} {post.content[:200]}")
        if len(self._posts) > 10:
            lines.append(f"  ... and {len(self._posts) - 10} earlier posts")
        return "\n".join(lines)
