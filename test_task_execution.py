"""
Tests for the redesigned task-oriented execution framework.
"""

import asyncio
import uuid
from wingent.core.task import Task, TaskStatus, TaskTree
from wingent.core.bulletin import BulletinBoard, BulletinPost, PostType
from wingent.core.tool import Tool, ToolDefinition, ToolParameter, ToolRegistry
from wingent.core.agent import AgentConfig, Agent, AgentContext, AgentRole, TurnResult
from wingent.core.executor import TaskExecutor
from wingent.core.tools.meta import SpawnSubtaskTool, CompleteTaskTool, PostToBulletinTool, ReadBulletinTool


# ── Mock Provider ──────────────────────────────────────────────────────────

class MockProvider:
    """Mock LLM provider that returns scripted responses.

    Supports tool-use simulation: if `tool_calls` is set in the script,
    it returns those tool calls. Otherwise returns text.
    """

    def __init__(self, responses=None):
        self.responses = responses or []
        self._call_index = 0
        self.call_log = []

    async def generate(self, messages, system, temperature, max_tokens,
                       tools=None, **kwargs):
        self.call_log.append({
            "messages": messages,
            "system": system,
            "tools": tools,
        })

        if self._call_index < len(self.responses):
            resp = self.responses[self._call_index]
            self._call_index += 1
            return resp

        # Default: complete task immediately
        return {
            "content": "",
            "tool_calls": [{
                "id": f"tc_{uuid.uuid4().hex[:8]}",
                "name": "complete_task",
                "input": {"result": "Default mock result"},
            }],
            "usage": {"input_tokens": 10, "output_tokens": 10, "total_tokens": 20},
            "model": "mock-model",
            "stop_reason": "tool_use",
        }


def make_text_response(text):
    return {
        "content": text,
        "tool_calls": [],
        "usage": {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
        "model": "mock-model",
        "stop_reason": "end_turn",
    }


def make_tool_call(name, input_dict, tool_id=None):
    return {
        "content": "",
        "tool_calls": [{
            "id": tool_id or f"tc_{uuid.uuid4().hex[:8]}",
            "name": name,
            "input": input_dict,
        }],
        "usage": {"input_tokens": 10, "output_tokens": 10, "total_tokens": 20},
        "model": "mock-model",
        "stop_reason": "tool_use",
    }


# ── Unit Tests: Data Models ───────────────────────────────────────────────

def test_task_lifecycle():
    """Test Task creation, completion, and failure."""
    task = Task(goal="Write a poem", completion_criteria="At least 4 lines")
    assert task.status == TaskStatus.PENDING
    assert not task.is_terminal()

    task.status = TaskStatus.IN_PROGRESS
    assert not task.is_terminal()

    task.complete("Roses are red...")
    assert task.status == TaskStatus.COMPLETED
    assert task.result == "Roses are red..."
    assert task.is_terminal()
    assert task.completed_at is not None
    print("  PASS: test_task_lifecycle")


def test_task_serialization():
    """Test Task to_dict/from_dict."""
    task = Task(goal="Test", completion_criteria="Passes")
    task.complete("Done")
    d = task.to_dict()
    restored = Task.from_dict(d)
    assert restored.goal == "Test"
    assert restored.status == TaskStatus.COMPLETED
    assert restored.result == "Done"
    print("  PASS: test_task_serialization")


def test_task_tree():
    """Test TaskTree operations."""
    tree = TaskTree()
    root = Task(id="root", goal="Root task")
    child1 = Task(id="c1", goal="Child 1", parent_task_id="root")
    child2 = Task(id="c2", goal="Child 2", parent_task_id="root")
    root.subtask_ids = ["c1", "c2"]

    tree.add_task(root)
    tree.add_task(child1)
    tree.add_task(child2)

    assert tree.get_task("root") is root
    assert len(tree.get_subtasks("root")) == 2
    assert len(tree.get_root_tasks()) == 1
    assert not tree.all_subtasks_complete("root")

    child1.complete("Done 1")
    assert not tree.all_subtasks_complete("root")

    child2.complete("Done 2")
    assert tree.all_subtasks_complete("root")

    lineage = tree.get_task_lineage("c1")
    assert len(lineage) == 2
    assert lineage[0].id == "c1"
    assert lineage[1].id == "root"

    assert tree.get_depth("c1") == 1
    assert tree.get_depth("root") == 0
    print("  PASS: test_task_tree")


def test_bulletin_board():
    """Test BulletinBoard posting and querying."""
    async def _test():
        board = BulletinBoard("task-1")
        board.subscribe("agent-a")
        board.subscribe("agent-b")

        post = BulletinPost(
            author_id="agent-a",
            post_type=PostType.STATUS_UPDATE,
            content="Working on it",
        )
        await board.post(post)

        # agent-b should receive notification
        received = await board.wait_for_post("agent-b", timeout=1.0)
        assert received is not None
        assert received.content == "Working on it"

        # agent-a should NOT receive own post
        received_self = await board.wait_for_post("agent-a", timeout=0.5)
        assert received_self is None

        # Query posts
        posts = board.get_posts(post_type=PostType.STATUS_UPDATE)
        assert len(posts) == 1

        # Summary
        summary = board.get_summary()
        assert "Working on it" in summary

    asyncio.run(_test())
    print("  PASS: test_bulletin_board")


def test_tool_registry():
    """Test ToolRegistry and ToolDefinition."""
    registry = ToolRegistry()
    registry.register(SpawnSubtaskTool())
    registry.register(CompleteTaskTool())

    assert len(registry) == 2
    assert "spawn_subtask" in registry
    assert "complete_task" in registry
    assert registry.get("spawn_subtask") is not None

    schemas = registry.to_llm_tools()
    assert len(schemas) == 2
    assert schemas[0]["name"] == "spawn_subtask"
    assert "input_schema" in schemas[0]
    print("  PASS: test_tool_registry")


# ── Integration Tests: Execution ──────────────────────────────────────────

def test_direct_completion():
    """Test an agent that completes a task directly (no decomposition)."""
    async def _test():
        provider = MockProvider(responses=[
            # Agent calls complete_task
            make_tool_call("complete_task", {"result": "The answer is 42"}),
            # After tool execution, agent gets tool result and ends turn
            make_text_response("Done."),
        ])

        def factory(provider_name, model):
            return provider

        config = AgentConfig(
            id="agent-1", name="Worker", provider="mock",
            model="mock-model", system_prompt="You solve tasks.",
        )
        executor = TaskExecutor(
            provider_factory=factory,
            default_agent_config=config,
        )

        task = await executor.submit("What is 6*7?", "A number")
        await executor.wait_for_completion(task, timeout=10)

        assert task.status == TaskStatus.COMPLETED
        assert task.result == "The answer is 42"
        assert executor._agent_count == 1

        stats = executor.get_statistics()
        assert stats["completed"] == 1
        assert stats["total_agents"] == 1

        await executor.shutdown()

    asyncio.run(_test())
    print("  PASS: test_direct_completion")


def test_decomposition():
    """Test an agent that decomposes into subtasks."""
    async def _test():
        call_count = 0

        class DecomposeProvider:
            """First agent decomposes; subtask agents complete directly."""
            async def generate(self, messages, system, temperature, max_tokens,
                               tools=None, **kwargs):
                nonlocal call_count
                call_count += 1

                # Check if this is a manager synthesizing
                for msg in messages:
                    if isinstance(msg.get("content"), str) and "All subtasks are now complete" in msg["content"]:
                        return make_tool_call("complete_task", {
                            "result": "Synthesized: research done + draft written"
                        })

                # Check if this is a worker agent (system prompt says "worker")
                if "worker agent" in system.lower():
                    return make_tool_call("complete_task", {
                        "result": f"Subtask result from call {call_count}"
                    })

                # Root agent: decompose
                return make_tool_call("spawn_subtask", {
                    "goal": "Research the topic",
                    "completion_criteria": "Summary of findings",
                })

        provider = DecomposeProvider()

        def factory(provider_name, model):
            return provider

        config = AgentConfig(
            id="root-agent", name="Coordinator", provider="mock",
            model="mock-model", system_prompt="You coordinate work.",
        )
        executor = TaskExecutor(
            provider_factory=factory,
            default_agent_config=config,
            max_turns_per_agent=10,
        )

        task = await executor.submit(
            "Write a research report",
            "A complete report with findings",
        )
        await executor.wait_for_completion(task, timeout=30)

        assert task.status == TaskStatus.COMPLETED, f"Task status: {task.status}, error: {task.error}"
        assert len(task.subtask_ids) >= 1
        assert executor._agent_count >= 2  # root + at least 1 worker

        stats = executor.get_statistics()
        assert stats["total_tasks"] >= 2
        assert stats["bulletin_boards"] >= 1

        await executor.shutdown()

    asyncio.run(_test())
    print("  PASS: test_decomposition")


def test_max_depth_limit():
    """Test that max_depth prevents infinite decomposition."""
    async def _test():
        class AlwaysDecomposeProvider:
            async def generate(self, messages, system, temperature, max_tokens,
                               tools=None, **kwargs):
                return make_tool_call("spawn_subtask", {
                    "goal": "Do more work",
                    "completion_criteria": "Something",
                })

        def factory(pn, m):
            return AlwaysDecomposeProvider()

        config = AgentConfig(
            id="root", name="Root", provider="mock",
            model="mock", system_prompt="test",
        )
        executor = TaskExecutor(
            provider_factory=factory,
            default_agent_config=config,
            max_depth=2,
            max_turns_per_agent=5,
        )

        task = await executor.submit("Deep task", "criteria")
        await executor.wait_for_completion(task, timeout=15)

        # Should eventually fail or complete (depth limit prevents infinite recursion)
        assert task.is_terminal()
        # The deepest agents should hit the depth limit error in spawn_subtask
        await executor.shutdown()

    asyncio.run(_test())
    print("  PASS: test_max_depth_limit")


def test_max_turns_limit():
    """Test that max_turns prevents infinite loops."""
    async def _test():
        class NeverFinishProvider:
            async def generate(self, messages, system, temperature, max_tokens,
                               tools=None, **kwargs):
                return make_text_response("Still thinking...")

        def factory(pn, m):
            return NeverFinishProvider()

        config = AgentConfig(
            id="root", name="Root", provider="mock",
            model="mock", system_prompt="test",
        )
        executor = TaskExecutor(
            provider_factory=factory,
            default_agent_config=config,
            max_turns_per_agent=3,
        )

        task = await executor.submit("Impossible task", "criteria")
        await executor.wait_for_completion(task, timeout=10)

        assert task.status == TaskStatus.FAILED
        assert "Max turns" in task.error
        await executor.shutdown()

    asyncio.run(_test())
    print("  PASS: test_max_turns_limit")


def test_agent_config_backward_compat():
    """Test that AgentConfig still works with old-style dict (no tool_names)."""
    old_dict = {
        "id": "a1", "name": "Agent", "provider": "anthropic",
        "model": "claude-sonnet-4-5-20250929", "system_prompt": "Hello",
        "temperature": 0.5, "max_tokens": 2048,
    }
    config = AgentConfig.from_dict(old_dict)
    assert config.tool_names == []
    assert config.can_spawn is True

    # New style
    new_dict = {**old_dict, "tool_names": ["web_search"], "can_spawn": False}
    config2 = AgentConfig.from_dict(new_dict)
    assert config2.tool_names == ["web_search"]
    assert config2.can_spawn is False
    print("  PASS: test_agent_config_backward_compat")


# ── Run all tests ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Unit Tests:")
    test_task_lifecycle()
    test_task_serialization()
    test_task_tree()
    test_bulletin_board()
    test_tool_registry()
    test_agent_config_backward_compat()

    print("\nIntegration Tests:")
    test_direct_completion()
    test_decomposition()
    test_max_depth_limit()
    test_max_turns_limit()

    print("\nAll tests passed!")
