"""
Agent configuration and runtime classes.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, List, Callable, Awaitable, TYPE_CHECKING
from enum import Enum
import time
import uuid

if TYPE_CHECKING:
    from .task import Task, TaskTree
    from .bulletin import BulletinBoard
    from .tool import ToolRegistry
    from ..providers.base import LLMProvider


@dataclass
class VisualPosition:
    """Visual position on canvas."""
    x: int
    y: int

    def to_dict(self) -> Dict[str, int]:
        return {"x": self.x, "y": self.y}

    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> 'VisualPosition':
        return cls(x=data["x"], y=data["y"])


@dataclass
class AgentConfig:
    """Configuration for a single agent."""
    id: str
    name: str
    provider: str  # "anthropic", "openai", "local"
    model: str
    system_prompt: str
    temperature: float = 0.7
    max_tokens: int = 4096
    tool_names: List[str] = field(default_factory=list)
    can_spawn: bool = True
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if data["metadata"] is None:
            data["metadata"] = {}
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentConfig':
        return cls(
            id=data["id"],
            name=data["name"],
            provider=data["provider"],
            model=data["model"],
            system_prompt=data["system_prompt"],
            temperature=data.get("temperature", 0.7),
            max_tokens=data.get("max_tokens", 4096),
            tool_names=data.get("tool_names", []),
            can_spawn=data.get("can_spawn", True),
            metadata=data.get("metadata")
        )


class AgentRole(Enum):
    WORKER = "worker"
    MANAGER = "manager"


@dataclass
class AgentContext:
    """Everything an agent needs for a turn."""
    task: 'Task'
    bulletin_board: Optional['BulletinBoard']
    task_tree: 'TaskTree'
    agent_spawner: Callable  # async callable to spawn subagents
    agent: Optional['Agent'] = None  # back-reference to the owning agent


@dataclass
class TurnResult:
    """Result of a single agent turn."""
    content: str = ""
    tool_calls_made: int = 0
    task_completed: bool = False
    subtasks_spawned: int = 0
    usage: Dict[str, int] = field(default_factory=dict)


@dataclass
class CompanionConfig:
    """Configuration for a lightweight companion agent."""
    provider: str
    model: str
    temperature: float = 0.3
    max_tokens: int = 1024


class CompanionAgent:
    """Lightweight, stateless agent for routine tasks (evaluation, summarization, etc.).

    Unlike the main Agent, a CompanionAgent:
    - Has no conversation history (each call is independent)
    - Has no tools (pure prompt-in, text-out)
    - Uses a cheaper/faster LLM
    - Is identified by a purpose string (e.g., "evaluator", "summarizer")
    """

    def __init__(self, purpose: str, system_prompt: str,
                 provider: 'LLMProvider', config: CompanionConfig):
        self.purpose = purpose
        self.system_prompt = system_prompt
        self.provider = provider
        self.config = config

    async def run(self, prompt: str) -> str:
        """Send a single prompt and return the text response."""
        messages = [{"role": "user", "content": prompt}]
        response = await self.provider.generate(
            messages=messages,
            system=self.system_prompt,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            model=self.config.model,
        )
        return response.get("content", "")


class Agent:
    """Runtime agent instance with tool-use loop."""

    def __init__(self, config: 'AgentConfig', provider: 'LLMProvider',
                 tools: 'ToolRegistry', level: int = 0,
                 parent: Optional['Agent'] = None):
        self.config = config
        self.provider = provider
        self.tools = tools
        self.role: AgentRole = AgentRole.MANAGER
        self.current_task_id: Optional[str] = None
        self.message_history: List[Dict[str, Any]] = []
        self.level: int = level
        self.parent: Optional['Agent'] = parent
        self.children: List['Agent'] = []
        self.companions: Dict[str, CompanionAgent] = {}
        if parent is not None:
            parent.children.append(self)

    async def run_turn(self, context: AgentContext) -> TurnResult:
        """Execute one reasoning turn with a tool-use loop.

        The agent:
        1. Builds context from task + bulletin board
        2. Calls LLM with tools
        3. If tool_use: executes tools, appends results, loops
        4. If end_turn: returns the text response
        """
        result = TurnResult()
        system_prompt = self._build_system_prompt(context)
        tool_schemas = self.tools.to_llm_tools() if len(self.tools) > 0 else None

        # Add task context as user message if history is empty
        if not self.message_history:
            self.message_history.append({
                "role": "user",
                "content": self._build_task_message(context),
            })

        max_tool_rounds = 20
        for _ in range(max_tool_rounds):
            response = await self.provider.generate(
                messages=self.message_history,
                system=system_prompt,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                tools=tool_schemas,
                model=self.config.model,
            )

            # Accumulate usage
            usage = response.get("usage", {})
            for key in ("input_tokens", "output_tokens", "total_tokens"):
                result.usage[key] = result.usage.get(key, 0) + usage.get(key, 0)

            tool_calls = response.get("tool_calls", [])
            content = response.get("content", "")
            stop_reason = response.get("stop_reason", "end_turn")

            if stop_reason == "tool_use" and tool_calls:
                # Append assistant message with tool use
                assistant_content = []
                if content:
                    assistant_content.append({"type": "text", "text": content})
                for tc in tool_calls:
                    assistant_content.append({
                        "type": "tool_use",
                        "id": tc["id"],
                        "name": tc["name"],
                        "input": tc["input"],
                    })
                self.message_history.append({
                    "role": "assistant",
                    "content": assistant_content,
                })

                # Execute each tool and collect results
                tool_results = []
                for tc in tool_calls:
                    tool = self.tools.get(tc["name"])
                    if tool:
                        try:
                            tool_output = await tool.execute(
                                context=context,
                                **tc["input"]
                            )
                        except Exception as e:
                            tool_output = f"Error: {e}"
                    else:
                        tool_output = f"Error: Unknown tool '{tc['name']}'"

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tc["id"],
                        "content": tool_output,
                    })
                    result.tool_calls_made += 1

                    # Track spawns and completions
                    if tc["name"] == "spawn_subtask":
                        result.subtasks_spawned += 1
                    elif tc["name"] == "complete_task":
                        result.task_completed = True

                self.message_history.append({
                    "role": "user",
                    "content": tool_results,
                })
            else:
                # End turn — append assistant text and return
                if content:
                    self.message_history.append({
                        "role": "assistant",
                        "content": content,
                    })
                result.content = content
                break

        return result

    def _build_system_prompt(self, context: AgentContext) -> str:
        parts = [self.config.system_prompt]

        parts.append(f"\n## Your Role: {self.role.value}")
        parts.append(f"\n## Current Task\nGoal: {context.task.goal}")
        parts.append(f"Completion Criteria: {context.task.completion_criteria}")
        parts.append(f"Status: {context.task.status.value}")

        if context.task.status.value == "decomposed":
            subtasks = context.task_tree.get_subtasks(context.task.id)
            if subtasks:
                parts.append("\n## Subtasks")
                for st in subtasks:
                    parts.append(f"- [{st.status.value}] {st.goal}")
                    if st.result:
                        parts.append(f"  Result: {st.result[:500]}")
                    if st.error:
                        parts.append(f"  Error: {st.error[:200]}")

        if context.bulletin_board:
            parts.append(f"\n## Bulletin Board\n{context.bulletin_board.get_summary()}")

        # Lineage context
        lineage = context.task_tree.get_task_lineage(context.task.id)
        if len(lineage) > 1:
            parts.append("\n## Task Hierarchy")
            for i, t in enumerate(reversed(lineage)):
                indent = "  " * i
                parts.append(f"{indent}{'>' if t.id == context.task.id else '-'} {t.goal}")

        return "\n".join(parts)

    def _build_task_message(self, context: AgentContext) -> str:
        parts = [f"Please work on the following task:"]
        parts.append(f"\nGoal: {context.task.goal}")
        parts.append(f"Completion Criteria: {context.task.completion_criteria}")

        if self.role == AgentRole.MANAGER:
            parts.append("\nAll subtasks are complete. Please synthesize the results and complete the parent task.")

        return "\n".join(parts)

    def add_companion(self, companion: CompanionAgent) -> None:
        """Register a companion agent by its purpose."""
        self.companions[companion.purpose] = companion

    def get_companion(self, purpose: str) -> Optional[CompanionAgent]:
        """Get a companion agent by purpose."""
        return self.companions.get(purpose)

    async def ask_companion(self, purpose: str, prompt: str) -> Optional[str]:
        """Invoke a companion agent by purpose. Returns None if not found."""
        companion = self.companions.get(purpose)
        if companion is None:
            return None
        return await companion.run(prompt)

    def add_context_message(self, content: str) -> None:
        """Add a user message to provide additional context."""
        self.message_history.append({"role": "user", "content": content})

    def clear_history(self) -> None:
        self.message_history.clear()
