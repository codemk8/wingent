"""
Load agent prompts from prompts.yaml.
"""

import os
import yaml
from typing import Optional

_prompts = None
_PROMPTS_PATH = os.path.join(os.path.dirname(__file__), "prompts.yaml")


def _load() -> dict:
    global _prompts
    if _prompts is None:
        with open(_PROMPTS_PATH, "r") as f:
            _prompts = yaml.safe_load(f)
    return _prompts


def get_manager_prompt(working_directory: Optional[str] = None) -> str:
    """Return the system prompt for agents that can spawn subtasks."""
    prompts = _load()
    parts = [prompts["manager"].strip()]
    if working_directory:
        ctx = prompts["working_directory_context"].strip().format(
            working_directory=working_directory
        )
        parts.append(ctx)
    return "\n".join(parts)


def get_worker_prompt(working_directory: Optional[str] = None) -> str:
    """Return the system prompt for leaf agents at max depth."""
    prompts = _load()
    parts = [prompts["worker"].strip()]
    if working_directory:
        ctx = prompts["working_directory_context"].strip().format(
            working_directory=working_directory
        )
        parts.append(ctx)
    return "\n".join(parts)


def reload():
    """Force reload prompts from disk (useful for hot-reloading)."""
    global _prompts
    _prompts = None
