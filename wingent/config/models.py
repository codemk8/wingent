"""
Provider model registry — loads from models.yaml, supports live refresh.
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).parent / "models.yaml"
_models: Optional[Dict[str, List[str]]] = None


def _load() -> Dict[str, List[str]]:
    global _models
    with open(_CONFIG_PATH) as f:
        _models = yaml.safe_load(f)
    return _models


def get_provider_models() -> Dict[str, List[str]]:
    """Return the full provider → model-list mapping."""
    if _models is None:
        _load()
    return _models


def get_models(provider: str) -> List[str]:
    """Return available models for a specific provider."""
    return get_provider_models().get(provider, [])


def refresh_openrouter() -> List[str]:
    """Fetch the current model list from OpenRouter's API and update the registry.

    Requires OPENROUTER_API_KEY to be set. Falls back to the cached list
    if the API call fails.
    """
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        logger.warning("OPENROUTER_API_KEY not set, skipping refresh")
        return get_models("openrouter")

    try:
        import httpx
        resp = httpx.get(
            "https://openrouter.ai/api/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning("Failed to fetch OpenRouter models: %s", e)
        return get_models("openrouter")

    models = []
    for item in data.get("data", []):
        model_id = item.get("id", "")
        if model_id:
            models.append(model_id)

    models.sort()

    if models:
        get_provider_models()["openrouter"] = models
        _save()
        logger.info("Updated OpenRouter models: %d models", len(models))

    return models


def _save() -> None:
    """Write the current model registry back to models.yaml."""
    if _models is None:
        return
    with open(_CONFIG_PATH, "w") as f:
        yaml.dump(_models, f, default_flow_style=False, sort_keys=False)


def reload() -> Dict[str, List[str]]:
    """Force reload from disk."""
    global _models
    _models = None
    return _load()
