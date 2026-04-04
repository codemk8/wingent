"""
Task execution endpoints.
"""

import os
import uuid
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..state import app_state
from ...core.agent import AgentConfig, CompanionConfig
from ...core.session import Session
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
    elif provider_name == "openrouter":
        from ...providers.openrouter import OpenRouterProvider
        return OpenRouterProvider()
    elif provider_name == "local":
        from ...providers.local import LocalProvider
        return LocalProvider()
    raise ValueError(f"Unknown provider: {provider_name}")


def _pick_companion_provider(main_provider: str) -> str:
    """Use OpenRouter for companions if API key is set, otherwise fall back to main provider."""
    if os.environ.get("OPENROUTER_API_KEY"):
        return "openrouter"
    return main_provider


def _default_companion_model(provider: str) -> str:
    """Pick a cheap/fast model for companion agents based on provider."""
    defaults = {
        "anthropic": "claude-haiku-4-5-20251001",  # cheapest Anthropic option
        "openai": "gpt-4o-mini",
        "openrouter": "google/gemini-2.5-flash",
        "local": "llama3",
    }
    return defaults.get(provider, "claude-haiku-4-5-20251001")


class TaskSubmitRequest(BaseModel):
    goal: str
    completion_criteria: str = ""
    agent_config_id: Optional[str] = None
    working_directory: Optional[str] = None
    provider: str = "anthropic"
    model: str = "claude-sonnet-4-6-20260401"


@router.post("")
async def submit_task(req: TaskSubmitRequest):
    """Submit a new task for execution.

    If a session already exists and is idle, the task is submitted to the
    existing root agent (which retains context from prior tasks).
    A new session is created when none exists or when the provider/model changes.
    """
    # Check if there's already a task in progress
    if app_state.session and any(
        not t.is_terminal() for t in app_state.session.task_tree.all_tasks()
    ):
        raise HTTPException(409, "A task is already running. Stop it first.")

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

    criteria = req.completion_criteria or "Complete the task thoroughly and report the result."

    # Companion config — prefer OpenRouter for cheap evaluation when available
    companion_provider = _pick_companion_provider(req.provider)
    companion_config = CompanionConfig(
        provider=companion_provider,
        model=_default_companion_model(companion_provider),
        temperature=0.2,
        max_tokens=256,
    )

    # Create session if none exists (or config changed)
    if not app_state.session:
        session = Session(
            provider_factory=_make_provider,
            agent_config=config,
            max_agents=10,
            max_turns_per_agent=20,
            working_directory=req.working_directory,
            companion_config=companion_config,
        )
        session.add_callback(app_state.ws_manager.execution_callback)
        app_state.session = session

    task = await app_state.session.submit(req.goal, criteria)

    return {
        "task_id": task.id,
        "status": task.status.value,
        "goal": task.goal,
        "session_id": app_state.session.id,
    }


@router.get("")
async def list_tasks():
    if not app_state.session:
        return []
    return [_task_to_dict(t) for t in app_state.session.task_tree.all_tasks()]


@router.get("/stats")
async def get_stats():
    if not app_state.session:
        return {"total_tasks": 0, "completed": 0, "failed": 0,
                "in_progress": 0, "decomposed": 0, "total_agents": 0,
                "bulletin_boards": 0}
    return app_state.session.get_statistics()


@router.get("/{task_id}")
async def get_task(task_id: str):
    if not app_state.session:
        raise HTTPException(404, "No active session")
    task = app_state.session.task_tree.get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    return _task_to_dict(task)


@router.post("/stop")
async def stop_execution():
    if not app_state.session:
        raise HTTPException(400, "No active session")
    await app_state.session.shutdown()
    return {"ok": True}


@router.post("/reset")
async def reset_session():
    """End the current session and clear the root agent's history."""
    if app_state.session:
        await app_state.session.shutdown()
    app_state.session = None
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
