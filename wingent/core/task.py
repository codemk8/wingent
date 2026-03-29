"""
Task model and task tree for hierarchical task management.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum
import uuid
import time


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DECOMPOSED = "decomposed"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Task:
    """A unit of work with a goal and completion criteria."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    goal: str = ""
    completion_criteria: str = ""
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[str] = None
    error: Optional[str] = None
    parent_task_id: Optional[str] = None
    subtask_ids: List[str] = field(default_factory=list)
    assigned_agent_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_terminal(self) -> bool:
        return self.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)

    def complete(self, result: str) -> None:
        self.status = TaskStatus.COMPLETED
        self.result = result
        self.completed_at = time.time()

    def fail(self, error: str) -> None:
        self.status = TaskStatus.FAILED
        self.error = error
        self.completed_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "goal": self.goal,
            "completion_criteria": self.completion_criteria,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "parent_task_id": self.parent_task_id,
            "subtask_ids": self.subtask_ids.copy(),
            "assigned_agent_id": self.assigned_agent_id,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "metadata": self.metadata.copy(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        return cls(
            id=data["id"],
            goal=data["goal"],
            completion_criteria=data["completion_criteria"],
            status=TaskStatus(data["status"]),
            result=data.get("result"),
            error=data.get("error"),
            parent_task_id=data.get("parent_task_id"),
            subtask_ids=data.get("subtask_ids", []),
            assigned_agent_id=data.get("assigned_agent_id"),
            created_at=data.get("created_at", time.time()),
            completed_at=data.get("completed_at"),
            metadata=data.get("metadata", {}),
        )


class TaskTree:
    """In-memory registry of all tasks in an execution."""

    def __init__(self):
        self._tasks: Dict[str, Task] = {}

    def add_task(self, task: Task) -> None:
        self._tasks[task.id] = task

    def get_task(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    def get_subtasks(self, task_id: str) -> List[Task]:
        task = self._tasks.get(task_id)
        if not task:
            return []
        return [self._tasks[sid] for sid in task.subtask_ids if sid in self._tasks]

    def get_root_tasks(self) -> List[Task]:
        return [t for t in self._tasks.values() if t.parent_task_id is None]

    def all_subtasks_complete(self, task_id: str) -> bool:
        subtasks = self.get_subtasks(task_id)
        if not subtasks:
            return False
        return all(t.is_terminal() for t in subtasks)

    def get_task_lineage(self, task_id: str) -> List[Task]:
        """Walk from task up to root. Returns [task, parent, grandparent, ...]."""
        lineage = []
        current_id = task_id
        while current_id:
            task = self._tasks.get(current_id)
            if not task:
                break
            lineage.append(task)
            current_id = task.parent_task_id
        return lineage

    def get_depth(self, task_id: str) -> int:
        return len(self.get_task_lineage(task_id)) - 1

    def all_tasks(self) -> List[Task]:
        return list(self._tasks.values())
