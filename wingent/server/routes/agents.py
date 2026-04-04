"""
Agent config CRUD endpoints.
"""

from typing import Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..state import app_state, AGENT_TEMPLATES, TOPOLOGY_TEMPLATES, PROVIDER_MODELS
from ...core.agent import AgentConfig

router = APIRouter(prefix="/api/agents", tags=["agents"])


class AgentConfigRequest(BaseModel):
    name: str
    provider: str = "anthropic"
    model: str = "claude-sonnet-4-5-20250929"
    system_prompt: str = ""
    temperature: float = 0.7
    max_tokens: int = 4096
    tool_names: list = Field(default_factory=list)
    can_spawn: bool = True
    position: Dict[str, int] = Field(default_factory=lambda: {"x": 250, "y": 250})


def _config_to_dict(config: AgentConfig) -> Dict[str, Any]:
    d = config.to_dict()
    d["position"] = (config.metadata or {}).get("position", {"x": 250, "y": 250})
    return d


@router.get("")
async def list_agents():
    return [_config_to_dict(c) for c in app_state.agent_configs.values()]


@router.post("")
async def create_agent(req: AgentConfigRequest):
    config = AgentConfig(
        id="",
        name=req.name,
        provider=req.provider,
        model=req.model,
        system_prompt=req.system_prompt,
        temperature=req.temperature,
        max_tokens=req.max_tokens,
        tool_names=req.tool_names,
        can_spawn=req.can_spawn,
        metadata={"position": req.position},
    )
    config = app_state.add_agent_config(config)
    return _config_to_dict(config)


@router.put("/{agent_id}")
async def update_agent(agent_id: str, req: AgentConfigRequest):
    if agent_id not in app_state.agent_configs:
        raise HTTPException(404, "Agent not found")
    config = AgentConfig(
        id=agent_id,
        name=req.name,
        provider=req.provider,
        model=req.model,
        system_prompt=req.system_prompt,
        temperature=req.temperature,
        max_tokens=req.max_tokens,
        tool_names=req.tool_names,
        can_spawn=req.can_spawn,
        metadata={"position": req.position},
    )
    app_state.agent_configs[agent_id] = config
    return _config_to_dict(config)


@router.delete("/{agent_id}")
async def delete_agent(agent_id: str):
    if not app_state.remove_agent_config(agent_id):
        raise HTTPException(404, "Agent not found")
    return {"ok": True}


@router.get("/templates")
async def list_templates():
    result = {}
    for key, config in AGENT_TEMPLATES.items():
        result[key] = {
            "name": config.name,
            "provider": config.provider,
            "model": config.model,
            "system_prompt": config.system_prompt,
            "temperature": config.temperature,
        }
    return result


@router.get("/topologies")
async def list_topologies():
    return {k: {"name": v["name"], "description": v["description"]}
            for k, v in TOPOLOGY_TEMPLATES.items()}


@router.post("/topologies/{name}/apply")
async def apply_topology(name: str):
    if name not in TOPOLOGY_TEMPLATES:
        raise HTTPException(404, "Topology not found")
    created = app_state.apply_topology(name)
    return [_config_to_dict(c) for c in created]


@router.get("/providers")
async def list_providers():
    return PROVIDER_MODELS


@router.post("/providers/openrouter/refresh")
async def refresh_openrouter_models():
    """Fetch the latest model list from the OpenRouter API."""
    from ...config.models import refresh_openrouter
    models = refresh_openrouter()
    return {"count": len(models), "models": models}
