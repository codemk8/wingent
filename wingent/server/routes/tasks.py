"""
Task execution endpoints.
"""

import uuid
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..state import app_state
from ...core.agent import AgentConfig
from ...core.executor import TaskExecutor
from ...core.prompts import get_manager_prompt

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


def _make_provider(provider_name: str, model: str):
    """Provider factory — lazily imports and instantiates providers."""
    if provider_name == "anthropic":
        from ...providers.anthropic import AnthropicProvider
        return AnthropicProvider()
    elif provider_name == "openai":
        from ...providers.openai import OpenAIProvider
        return OpenAIProvider()
    elif provider_name == "local":
        from ...providers.local import LocalProvider
        return LocalProvider()
    raise ValueError(f"Unknown provider: {provider_name}")


class TaskSubmitRequest(BaseModel):
    goal: str
    completion_criteria: str = ""
    agent_config_id: Optional[str] = None
    working_directory: Optional[str] = None
    provider: str = "anthropic"
    model: str = "claude-sonnet-4-5-20250929"


@router.post("")
async def submit_task(req: TaskSubmitRequest):
    """Submit a new root task for execution.

    If no agent_config_id is provided, a default root agent is created
    automatically — the framework decides what agents to spawn.
    """
    if app_state.executor and any(
        not t.is_terminal() for t in app_state.executor.task_tree.all_tasks()
    ):
        raise HTTPException(409, "An execution is already running. Stop it first.")

    if req.working_directory:
        app_state.working_directory = req.working_directory

    # Pick or create agent config
    if req.agent_config_id and req.agent_config_id in app_state.agent_configs:
        config = app_state.agent_configs[req.agent_config_id]
    else:
        config = AgentConfig(
            id=str(uuid.uuid4()),
            name="Root Agent",
            provider=req.provider,
            model=req.model,
            system_prompt=get_manager_prompt(req.working_directory),
            temperature=0.3,
            max_tokens=4096,
        )

    # Auto-generate completion criteria if not provided
    criteria = req.completion_criteria or "Complete the task thoroughly and report the result."

    # Create executor
    executor = TaskExecutor(
        provider_factory=_make_provider,
        default_agent_config=config,
        max_depth=3,
        max_agents=10,
        max_turns_per_agent=20,
        working_directory=req.working_directory,
    )
    executor.add_callback(app_state.ws_manager.execution_callback)
    app_state.executor = executor

    task = await executor.submit(req.goal, criteria, config)

    return {
        "task_id": task.id,
        "status": task.status.value,
        "goal": task.goal,
    }


@router.get("")
async def list_tasks():
    if not app_state.executor:
        return []
    return [_task_to_dict(t) for t in app_state.executor.task_tree.all_tasks()]


@router.get("/stats")
async def get_stats():
    if not app_state.executor:
        return {"total_tasks": 0, "completed": 0, "failed": 0,
                "in_progress": 0, "decomposed": 0, "total_agents": 0,
                "bulletin_boards": 0}
    return app_state.executor.get_statistics()


@router.get("/{task_id}")
async def get_task(task_id: str):
    if not app_state.executor:
        raise HTTPException(404, "No execution running")
    task = app_state.executor.task_tree.get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    return _task_to_dict(task)


@router.post("/stop")
async def stop_execution():
    if not app_state.executor:
        raise HTTPException(400, "No execution running")
    await app_state.executor.shutdown()
    return {"ok": True}


def _task_to_dict(task):
    return {
        "id": task.id,
        "goal": task.goal,
        "completion_criteria": task.completion_criteria,
        "status": task.status.value,
        "result": task.result,
        "error": task.error,
        "parent_task_id": task.parent_task_id,
        "subtask_ids": task.subtask_ids,
        "assigned_agent_id": task.assigned_agent_id,
        "created_at": task.created_at,
        "completed_at": task.completed_at,
    }
