"""
Shared application state for the FastAPI server.
"""

from typing import Dict, Optional
import uuid

from ..core.agent import AgentConfig
from ..core.executor import TaskExecutor
from .ws import WebSocketManager

# Agent type templates (ported from wingent/ui/explorer.py)
AGENT_TEMPLATES = {
    "researcher": AgentConfig(
        id="", name="Researcher", provider="anthropic",
        model="claude-sonnet-4-5-20250929",
        system_prompt="You are a research specialist. Find, analyze, and synthesize information thoroughly. Cite sources when possible.",
        temperature=0.3,
    ),
    "writer": AgentConfig(
        id="", name="Writer", provider="anthropic",
        model="claude-sonnet-4-5-20250929",
        system_prompt="You are a skilled writer. Create clear, engaging, well-structured content based on the information provided.",
        temperature=0.7,
    ),
    "editor": AgentConfig(
        id="", name="Editor", provider="anthropic",
        model="claude-sonnet-4-5-20250929",
        system_prompt="You are a meticulous editor. Review content for clarity, accuracy, grammar, and style. Suggest specific improvements.",
        temperature=0.3,
    ),
    "analyst": AgentConfig(
        id="", name="Analyst", provider="anthropic",
        model="claude-sonnet-4-5-20250929",
        system_prompt="You are a data analyst. Examine data and information to identify patterns, trends, and actionable insights.",
        temperature=0.2,
    ),
    "critic": AgentConfig(
        id="", name="Critic", provider="anthropic",
        model="claude-sonnet-4-5-20250929",
        system_prompt="You are a constructive critic. Evaluate work objectively, identify weaknesses, and suggest improvements.",
        temperature=0.4,
    ),
    "moderator": AgentConfig(
        id="", name="Moderator", provider="anthropic",
        model="claude-sonnet-4-5-20250929",
        system_prompt="You are a discussion moderator. Synthesize different viewpoints, identify consensus, and resolve conflicts.",
        temperature=0.5,
    ),
    "code_reviewer": AgentConfig(
        id="", name="Code Reviewer", provider="anthropic",
        model="claude-sonnet-4-5-20250929",
        system_prompt="You are a senior code reviewer. Analyze code for bugs, security issues, performance, and best practices.",
        temperature=0.2,
    ),
    "summarizer": AgentConfig(
        id="", name="Summarizer", provider="anthropic",
        model="claude-sonnet-4-5-20250929",
        system_prompt="You are a summarization expert. Distill complex information into concise, accurate summaries.",
        temperature=0.3,
    ),
    "planner": AgentConfig(
        id="", name="Planner", provider="anthropic",
        model="claude-sonnet-4-5-20250929",
        system_prompt="You are a strategic planner. Break down complex goals into actionable steps with clear priorities and timelines.",
        temperature=0.4,
    ),
    "translator": AgentConfig(
        id="", name="Translator", provider="anthropic",
        model="claude-sonnet-4-5-20250929",
        system_prompt="You are a professional translator. Translate content accurately while preserving tone, nuance, and cultural context.",
        temperature=0.2,
    ),
}

# Topology templates (ported from wingent/ui/explorer.py)
TOPOLOGY_TEMPLATES = {
    "research_pipeline": {
        "name": "Research Pipeline",
        "description": "Linear pipeline: Researcher → Writer → Editor",
        "agents": [
            {"template": "researcher", "position": {"x": 100, "y": 200}},
            {"template": "writer", "position": {"x": 350, "y": 200}},
            {"template": "editor", "position": {"x": 600, "y": 200}},
        ],
    },
    "debate_system": {
        "name": "Debate System",
        "description": "Two opposing viewpoints converge at a moderator",
        "agents": [
            {"template": "critic", "position": {"x": 100, "y": 100}, "name": "Advocate"},
            {"template": "critic", "position": {"x": 100, "y": 300}},
            {"template": "moderator", "position": {"x": 400, "y": 200}},
        ],
    },
    "parallel_analysis": {
        "name": "Parallel Analysis",
        "description": "Multiple analysts work in parallel, results synthesized",
        "agents": [
            {"template": "analyst", "position": {"x": 100, "y": 100}, "name": "Analyst A"},
            {"template": "analyst", "position": {"x": 100, "y": 300}, "name": "Analyst B"},
            {"template": "summarizer", "position": {"x": 400, "y": 200}},
        ],
    },
    "review_chain": {
        "name": "Review Chain",
        "description": "Draft → Review → Finalize pipeline",
        "agents": [
            {"template": "writer", "position": {"x": 100, "y": 200}, "name": "Drafter"},
            {"template": "code_reviewer", "position": {"x": 350, "y": 200}, "name": "Reviewer"},
            {"template": "editor", "position": {"x": 600, "y": 200}, "name": "Finalizer"},
        ],
    },
}

# Provider → model mapping
PROVIDER_MODELS = {
    "anthropic": [
        "claude-opus-4-5-20251101",
        "claude-sonnet-4-5-20250929",
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
    ],
    "openai": [
        "gpt-4-turbo",
        "gpt-4",
        "gpt-3.5-turbo",
    ],
    "openrouter": [
        "google/gemini-2.0-flash-001",
        "meta-llama/llama-3.3-70b-instruct",
        "mistralai/mistral-small-2501",
        "qwen/qwen-2.5-72b-instruct",
        "anthropic/claude-3.5-haiku",
        "openai/gpt-4o-mini",
        "google/gemini-2.5-pro-preview",
        "anthropic/claude-sonnet-4",
        "openai/gpt-4o",
        "deepseek/deepseek-chat-v3-0324",
    ],
    "local": [
        "llama3",
        "mistral",
        "codellama",
        "phi3",
    ],
}


class AppState:
    """Singleton holding the server's runtime state."""

    def __init__(self):
        self.agent_configs: Dict[str, AgentConfig] = {}
        self.executor: Optional[TaskExecutor] = None
        self.ws_manager = WebSocketManager()
        self.working_directory: Optional[str] = None

    def add_agent_config(self, config: AgentConfig) -> AgentConfig:
        if not config.id:
            config.id = str(uuid.uuid4())
        self.agent_configs[config.id] = config
        return config

    def remove_agent_config(self, agent_id: str) -> bool:
        if agent_id in self.agent_configs:
            del self.agent_configs[agent_id]
            return True
        return False

    def apply_topology(self, template_name: str) -> list:
        """Replace all agent configs with a topology template."""
        template = TOPOLOGY_TEMPLATES.get(template_name)
        if not template:
            return []

        self.agent_configs.clear()
        created = []
        for agent_def in template["agents"]:
            base = AGENT_TEMPLATES[agent_def["template"]]
            config = AgentConfig(
                id=str(uuid.uuid4()),
                name=agent_def.get("name", base.name),
                provider=base.provider,
                model=base.model,
                system_prompt=base.system_prompt,
                temperature=base.temperature,
                max_tokens=base.max_tokens,
                metadata={"position": agent_def["position"]},
            )
            self.agent_configs[config.id] = config
            created.append(config)
        return created


# Global singleton
app_state = AppState()
