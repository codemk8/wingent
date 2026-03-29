"""
Run a task through the new framework with a real LLM.

Usage:
    # Direct completion (agent solves it itself)
    python run_task.py "What are the 3 largest oceans?" "A list of 3 oceans"

    # Task that may decompose
    python run_task.py "Write a short pros/cons analysis of Python vs Rust" "A balanced comparison"

Requires ANTHROPIC_API_KEY env var (or change provider below).
"""

import asyncio
import sys
import time

from wingent.core.agent import AgentConfig
from wingent.core.executor import TaskExecutor


def make_provider(provider_name, model):
    """Provider factory — swap this to use OpenAI or local."""
    if provider_name == "anthropic":
        from wingent.providers.anthropic import AnthropicProvider
        return AnthropicProvider()
    elif provider_name == "openai":
        from wingent.providers.openai import OpenAIProvider
        return OpenAIProvider()
    elif provider_name == "local":
        from wingent.providers.local import LocalProvider
        return LocalProvider()
    raise ValueError(f"Unknown provider: {provider_name}")


def on_event(event, data):
    """Print execution events in real time."""
    ts = time.strftime("%H:%M:%S")
    if event == "task_started":
        print(f"[{ts}] Task started, agent={data['agent_id'][:8]}...")
    elif event == "turn_completed":
        preview = data.get("content_preview", "")[:80]
        print(f"[{ts}] Turn {data['turn']}: {data['tool_calls']} tool calls. {preview}")
    elif event == "subtask_spawned":
        print(f"[{ts}] Subtask spawned: {data['goal'][:60]}...")
    elif event == "manager_started":
        print(f"[{ts}] Agent became manager, monitoring subtasks...")
    elif event == "task_completed":
        print(f"[{ts}] Task completed!")
    elif event == "task_failed":
        print(f"[{ts}] Task FAILED: {data['error']}")


async def main():
    if len(sys.argv) < 3:
        print("Usage: python run_task.py <goal> <completion_criteria>")
        print('Example: python run_task.py "List 3 oceans" "A list of 3"')
        sys.exit(1)

    goal = sys.argv[1]
    criteria = sys.argv[2]

    config = AgentConfig(
        id="root",
        name="Root Agent",
        provider="anthropic",
        model="claude-sonnet-4-5-20250929",
        system_prompt=(
            "You are a capable agent. For simple tasks, solve them directly "
            "and call complete_task with your answer. For complex tasks that "
            "have multiple distinct parts, use spawn_subtask to break them "
            "down. Always call complete_task when you are done."
        ),
        temperature=0.3,
        max_tokens=4096,
    )

    executor = TaskExecutor(
        provider_factory=make_provider,
        default_agent_config=config,
        max_depth=2,
        max_agents=5,
        max_turns_per_agent=10,
    )
    executor.add_callback(on_event)

    print(f"Goal: {goal}")
    print(f"Criteria: {criteria}")
    print("-" * 60)

    task = await executor.submit(goal, criteria)
    await executor.wait_for_completion(task, timeout=120)

    print("-" * 60)
    print(f"Status: {task.status.value}")
    if task.result:
        print(f"\nResult:\n{task.result}")
    if task.error:
        print(f"\nError: {task.error}")

    stats = executor.get_statistics()
    print(f"\nStats: {stats}")

    await executor.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
