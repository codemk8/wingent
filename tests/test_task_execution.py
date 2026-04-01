"""
Tests for the redesigned task-oriented execution framework.
"""

import asyncio
import uuid
from wingent.core.task import Task, TaskStatus, TaskTree
from wingent.core.bulletin import BulletinBoard, BulletinPost, PostType
from wingent.core.tool import Tool, ToolDefinition, ToolParameter, ToolRegistry
from wingent.core.agent import AgentConfig, Agent, AgentContext, AgentRole, TurnResult, CompanionAgent, CompanionConfig
from wingent.core.executor import TaskExecutor
from wingent.core.tools.meta import SpawnSubtaskTool, CompleteTaskTool, PostToBulletinTool, ReadBulletinTool
from wingent.core.prompts import get_manager_prompt, get_worker_prompt, get_companion_prompt, reload as reload_prompts


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


def test_subtask_agents_cannot_spawn():
    """Test that subtask agents are workers and cannot decompose further."""
    async def _test():
        call_count = 0

        class TestProvider:
            async def generate(self, messages, system, temperature, max_tokens,
                               tools=None, **kwargs):
                nonlocal call_count
                call_count += 1

                # Manager synthesizing
                for msg in messages:
                    if isinstance(msg.get("content"), str) and "All subtasks are now complete" in msg["content"]:
                        return make_tool_call("complete_task", {"result": "Synthesized"})

                # Root: spawn one subtask
                if call_count == 1:
                    return make_tool_call("spawn_subtask", {
                        "goal": "Sub work",
                        "completion_criteria": "Done",
                    })

                # Subtask worker: complete directly
                return make_tool_call("complete_task", {"result": "Worker done"})

        def factory(pn, m):
            return TestProvider()

        config = AgentConfig(
            id="root", name="Root", provider="mock",
            model="mock", system_prompt="test",
        )
        executor = TaskExecutor(
            provider_factory=factory,
            default_agent_config=config,
            max_turns_per_agent=5,
        )

        task = await executor.submit("Deep task", "criteria")
        await executor.wait_for_completion(task, timeout=15)

        assert task.status == TaskStatus.COMPLETED

        # All subtask agents should be workers with can_spawn=False
        for agent in executor.agents.values():
            if agent.level > 0:
                assert agent.role == AgentRole.WORKER
                assert agent.config.can_spawn is False

        await executor.shutdown()

    asyncio.run(_test())
    print("  PASS: test_subtask_agents_cannot_spawn")


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


# ── Unit Tests: Prompts ──────────────────────────────────────────────────

def test_prompts_loader():
    """Test that prompts load from YAML and contain expected content."""
    reload_prompts()

    manager = get_manager_prompt()
    assert "autonomous agent" in manager
    assert "spawn_subtask" in manager

    worker = get_worker_prompt()
    assert "worker agent" in worker
    assert "cannot spawn" in worker.lower()

    evaluator = get_companion_prompt("evaluator")
    assert "PASS" in evaluator
    assert "FAIL" in evaluator

    # With working directory
    manager_wd = get_manager_prompt("/home/user/project")
    assert "/home/user/project" in manager_wd

    worker_wd = get_worker_prompt("/tmp/work")
    assert "/tmp/work" in worker_wd

    # Unknown purpose should raise
    try:
        get_companion_prompt("nonexistent")
        assert False, "Should have raised KeyError"
    except KeyError:
        pass

    print("  PASS: test_prompts_loader")


# ── Unit Tests: Companion Agent ──────────────────────────────────────────

def test_companion_agent():
    """Test CompanionAgent creation and run."""
    async def _test():
        mock_provider = MockProvider(responses=[
            make_text_response("PASS"),
        ])
        config = CompanionConfig(provider="mock", model="mock-model")
        companion = CompanionAgent(
            purpose="evaluator",
            system_prompt="You evaluate tasks.",
            provider=mock_provider,
            config=config,
        )

        assert companion.purpose == "evaluator"
        result = await companion.run("Is this good?")
        assert result == "PASS"

        # Verify it was called with correct structure
        assert len(mock_provider.call_log) == 1
        assert mock_provider.call_log[0]["system"] == "You evaluate tasks."
        assert mock_provider.call_log[0]["messages"][0]["content"] == "Is this good?"

    asyncio.run(_test())
    print("  PASS: test_companion_agent")


def test_agent_companion_registry():
    """Test Agent.add_companion / get_companion / ask_companion."""
    async def _test():
        mock_provider = MockProvider(responses=[
            make_text_response("Done."),
        ])
        registry = ToolRegistry()
        config = AgentConfig(
            id="a1", name="Agent", provider="mock",
            model="mock", system_prompt="test",
        )
        agent = Agent(config, mock_provider, registry)

        # No companion yet
        assert agent.get_companion("evaluator") is None
        result = await agent.ask_companion("evaluator", "test")
        assert result is None

        # Add companion
        eval_provider = MockProvider(responses=[
            make_text_response("FAIL\nReason: Missing details"),
        ])
        companion = CompanionAgent(
            purpose="evaluator",
            system_prompt="Evaluate.",
            provider=eval_provider,
            config=CompanionConfig(provider="mock", model="mock"),
        )
        agent.add_companion(companion)

        assert agent.get_companion("evaluator") is companion
        result = await agent.ask_companion("evaluator", "Check this")
        assert "FAIL" in result

    asyncio.run(_test())
    print("  PASS: test_agent_companion_registry")


# ── Unit Tests: Agent Hierarchy ──────────────────────────────────────────

def test_agent_hierarchy():
    """Test agent level, parent, and children tracking."""
    mock_provider = MockProvider()
    registry = ToolRegistry()

    root_config = AgentConfig(
        id="root", name="Root", provider="mock",
        model="mock", system_prompt="root",
    )
    root = Agent(root_config, mock_provider, registry, level=0)
    assert root.level == 0
    assert root.parent is None
    assert root.children == []

    child_config = AgentConfig(
        id="child", name="Child", provider="mock",
        model="mock", system_prompt="child",
    )
    child = Agent(child_config, mock_provider, registry, level=1, parent=root)
    assert child.level == 1
    assert child.parent is root
    assert root.children == [child]

    grandchild_config = AgentConfig(
        id="gc", name="Grandchild", provider="mock",
        model="mock", system_prompt="gc",
    )
    grandchild = Agent(grandchild_config, mock_provider, registry, level=2, parent=child)
    assert grandchild.level == 2
    assert grandchild.parent is child
    assert child.children == [grandchild]
    assert root.children == [child]  # root still only has direct child

    print("  PASS: test_agent_hierarchy")


def test_default_role_is_manager():
    """Test that new agents default to MANAGER role."""
    mock_provider = MockProvider()
    registry = ToolRegistry()
    config = AgentConfig(
        id="a1", name="Agent", provider="mock",
        model="mock", system_prompt="test",
    )
    agent = Agent(config, mock_provider, registry)
    assert agent.role == AgentRole.MANAGER
    print("  PASS: test_default_role_is_manager")


# ── Integration Tests: Evaluator Termination ─────────────────────────────

def test_evaluator_pass():
    """Test that complete_task succeeds when evaluator returns PASS."""
    async def _test():
        eval_provider = MockProvider(responses=[
            make_text_response("PASS"),
        ])

        class CompanionProvider:
            async def generate(self, messages, system, temperature, max_tokens,
                               tools=None, **kwargs):
                if "complexity analyst" in system:
                    return make_text_response("DECISION: direct\nReason: Simple math")
                if "planning specialist" in system:
                    return make_text_response("PLAN:\n- Compute 6*7")
                return make_text_response("PASS")

        main_provider = MockProvider(responses=[
            make_tool_call("complete_task", {"result": "The answer is 42"}),
            make_text_response("Done."),
        ])

        companion = CompanionProvider()

        def factory(provider_name, model):
            if model == "companion-mock":
                return companion
            return main_provider

        config = AgentConfig(
            id="agent-1", name="Worker", provider="mock",
            model="mock", system_prompt="Solve tasks.",
        )

        companion_config = CompanionConfig(provider="mock", model="companion-mock")
        executor = TaskExecutor(
            provider_factory=factory,
            default_agent_config=config,
            companion_config=companion_config,
        )

        task = await executor.submit("What is 6*7?", "A number")

        # Patch the evaluator provider on the created agent
        agent = list(executor.agents.values())[0]
        agent.companions["evaluator"].provider = eval_provider

        await executor.wait_for_completion(task, timeout=10)

        assert task.status == TaskStatus.COMPLETED
        assert task.result == "The answer is 42"

        # Evaluator was called once
        assert len(eval_provider.call_log) == 1
        assert "6*7" in eval_provider.call_log[0]["messages"][0]["content"]

        await executor.shutdown()

    asyncio.run(_test())
    print("  PASS: test_evaluator_pass")


def test_evaluator_fail_then_pass():
    """Test that evaluator rejection feeds back to agent, which retries."""
    async def _test():
        eval_provider = MockProvider(responses=[
            make_text_response("FAIL\nReason: Answer is incomplete"),
            make_text_response("PASS"),
        ])
        planner_provider = MockProvider(responses=[
            make_text_response("APPROACH: direct\n\nPLAN:\n- Compute 6*7 with detail"),
        ])

        main_provider = MockProvider(responses=[
            # First attempt: agent submits incomplete answer
            make_tool_call("complete_task", {"result": "42"}),
            # After rejection, agent revises and tries again
            make_tool_call("complete_task", {"result": "The answer is 42, which is 6 multiplied by 7."}),
            make_text_response("Done."),
        ])

        def factory(provider_name, model):
            if model == "companion-mock":
                return planner_provider
            return main_provider

        config = AgentConfig(
            id="agent-1", name="Worker", provider="mock",
            model="mock", system_prompt="Solve tasks.",
        )

        companion_config = CompanionConfig(provider="mock", model="companion-mock")
        executor = TaskExecutor(
            provider_factory=factory,
            default_agent_config=config,
            companion_config=companion_config,
        )

        task = await executor.submit("What is 6*7?", "A detailed answer")

        # Patch evaluator
        agent = list(executor.agents.values())[0]
        agent.companions["evaluator"].provider = eval_provider

        await executor.wait_for_completion(task, timeout=10)

        assert task.status == TaskStatus.COMPLETED
        assert "6 multiplied by 7" in task.result

        # Evaluator was called twice (fail then pass)
        assert len(eval_provider.call_log) == 2

        await executor.shutdown()

    asyncio.run(_test())
    print("  PASS: test_evaluator_fail_then_pass")


def test_all_subtask_agents_are_workers():
    """Test that all subtask agents get WORKER role regardless of depth."""
    async def _test():
        call_count = 0

        class TestProvider:
            async def generate(self, messages, system, temperature, max_tokens,
                               tools=None, **kwargs):
                nonlocal call_count
                call_count += 1

                # Manager synthesizing
                for msg in messages:
                    if isinstance(msg.get("content"), str) and "All subtasks are now complete" in msg["content"]:
                        return make_tool_call("complete_task", {"result": "Synthesized"})

                # Root: spawn one subtask
                if call_count == 1:
                    return make_tool_call("spawn_subtask", {
                        "goal": "Sub work",
                        "completion_criteria": "Done",
                    })

                # Worker completes directly
                return make_tool_call("complete_task", {"result": "Worker done"})

        def factory(pn, m):
            return TestProvider()

        config = AgentConfig(
            id="root", name="Root", provider="mock",
            model="mock", system_prompt="Coordinate.",
        )
        executor = TaskExecutor(
            provider_factory=factory,
            default_agent_config=config,
            max_turns_per_agent=10,
        )

        task = await executor.submit("Deep task", "criteria")
        await executor.wait_for_completion(task, timeout=15)

        assert task.status == TaskStatus.COMPLETED

        # All child agents should be workers
        child_agents = [a for a in executor.agents.values() if a.level > 0]
        assert len(child_agents) >= 1
        for child in child_agents:
            assert child.role == AgentRole.WORKER
            assert child.config.can_spawn is False

        await executor.shutdown()

    asyncio.run(_test())
    print("  PASS: test_all_subtask_agents_are_workers")


def test_evaluator_rejects_incomplete_task():
    """Test that the evaluator detects an incomplete result and prevents task completion.

    Scenario: Agent is asked to write a 3-step plan but only provides 1 step.
    The evaluator rejects it. The agent ends its turn without retrying,
    and with only 1 turn allowed the task fails — proving the evaluator
    blocked premature completion.
    """
    async def _test():
        eval_provider = MockProvider(responses=[
            # Evaluator rejects: result doesn't meet criteria
            make_text_response(
                "FAIL\n"
                "Reason: The task requires a 3-step plan but the result "
                "only contains 1 step. Steps 2 and 3 are missing."
            ),
        ])

        planner_provider = MockProvider(responses=[
            make_text_response("APPROACH: direct\n\nPLAN:\n- Write 3 steps"),
        ])

        main_provider = MockProvider(responses=[
            # Agent submits an incomplete result
            make_tool_call("complete_task", {"result": "Step 1: Gather requirements."}),
            # After rejection feedback, agent ends turn without retrying
            make_text_response("I need to think more..."),
        ])

        def factory(provider_name, model):
            if model == "companion-mock":
                return planner_provider
            return main_provider

        config = AgentConfig(
            id="agent-1", name="Planner", provider="mock",
            model="mock", system_prompt="You create plans.",
        )
        companion_config = CompanionConfig(provider="mock", model="companion-mock")
        executor = TaskExecutor(
            provider_factory=factory,
            default_agent_config=config,
            companion_config=companion_config,
            # Only 1 turn: agent cannot retry after the evaluator rejects
            max_turns_per_agent=1,
        )

        task = await executor.submit(
            "Create a 3-step project plan",
            "Must contain exactly 3 numbered steps",
        )

        # Patch evaluator onto the created agent
        agent = list(executor.agents.values())[0]
        agent.companions["evaluator"].provider = eval_provider

        await executor.wait_for_completion(task, timeout=10)

        # Task should NOT be completed — evaluator blocked it, then max turns hit
        assert task.status == TaskStatus.FAILED, (
            f"Expected FAILED but got {task.status}. "
            f"The evaluator should have prevented completion."
        )
        assert task.result is None, "Result should be None since evaluator rejected it"

        # Verify evaluator was called exactly once with the right context
        assert len(eval_provider.call_log) == 1
        eval_prompt = eval_provider.call_log[0]["messages"][0]["content"]
        assert "3-step project plan" in eval_prompt
        assert "Step 1: Gather requirements" in eval_prompt
        assert "exactly 3 numbered steps" in eval_prompt

        # Verify the agent received the rejection feedback in its conversation
        rejection_found = False
        for msg in agent.message_history:
            content = msg.get("content", "")
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and "FAILED" in block.get("content", ""):
                        rejection_found = True
            elif isinstance(content, str) and "FAILED" in content:
                rejection_found = True
        assert rejection_found, "Agent should have received evaluator rejection feedback"

        await executor.shutdown()

    asyncio.run(_test())
    print("  PASS: test_evaluator_rejects_incomplete_task")


def test_companion_config_wiring():
    """Test that executor creates evaluator companions on all agents."""
    async def _test():
        main_provider = MockProvider(responses=[
            make_tool_call("complete_task", {"result": "Done"}),
            make_text_response("Ok."),
        ])

        # Mock evaluator that always passes
        class PassProvider:
            call_log = []
            async def generate(self, messages, system, temperature, max_tokens,
                               tools=None, **kwargs):
                self.call_log.append(True)
                return {
                    "content": "PASS", "tool_calls": [],
                    "usage": {"input_tokens": 5, "output_tokens": 5, "total_tokens": 10},
                    "model": "mock", "stop_reason": "end_turn",
                }

        pass_provider = PassProvider()

        def factory(provider_name, model):
            if model == "cheap-model":
                return pass_provider
            return main_provider

        config = AgentConfig(
            id="a1", name="Agent", provider="mock",
            model="main-model", system_prompt="test",
        )
        companion_config = CompanionConfig(
            provider="mock", model="cheap-model",
            temperature=0.2, max_tokens=256,
        )
        executor = TaskExecutor(
            provider_factory=factory,
            default_agent_config=config,
            companion_config=companion_config,
        )

        task = await executor.submit("Test task", "criteria")
        await executor.wait_for_completion(task, timeout=10)

        # Agent should have an evaluator companion
        agent = list(executor.agents.values())[0]
        assert "evaluator" in agent.companions
        assert agent.companions["evaluator"].purpose == "evaluator"

        # Evaluator should have been called (task was completed)
        assert task.status == TaskStatus.COMPLETED
        assert len(pass_provider.call_log) >= 1

        await executor.shutdown()

    asyncio.run(_test())
    print("  PASS: test_companion_config_wiring")


# ── Unit Tests: Plan Parsing ──────────────────────────────────────────────

def test_parse_decision():
    """Test parsing decomposer output."""
    assert TaskExecutor._parse_decision("DECISION: direct\nReason: simple task") == "direct"
    assert TaskExecutor._parse_decision("DECISION: decompose\nReason: complex") == "decompose"
    assert TaskExecutor._parse_decision("DECISION: DECOMPOSE\nReason: caps") == "decompose"
    # Malformed — defaults to direct
    assert TaskExecutor._parse_decision("I think we should split this") == "direct"
    assert TaskExecutor._parse_decision("") == "direct"
    print("  PASS: test_parse_decision")


def test_parse_plan():
    """Test parsing planner output."""
    plan_text = (
        "PLAN:\n"
        "- Research the topic thoroughly\n"
        "- Write the first draft\n"
        "- Edit and finalize\n"
    )
    _, steps = TaskExecutor._parse_plan(plan_text)
    assert len(steps) == 3
    assert steps[0] == "Research the topic thoroughly"
    assert steps[2] == "Edit and finalize"

    # Empty / malformed
    _, steps = TaskExecutor._parse_plan("")
    assert steps == []

    _, steps = TaskExecutor._parse_plan("Just do stuff")
    assert steps == []

    print("  PASS: test_parse_plan")


# ── Integration Tests: Planner Auto-Decomposition ────────────────────────

def test_planner_auto_decompose():
    """Test that a decompose plan auto-spawns subtasks without agent turns."""
    async def _test():
        call_count = 0

        class MainProvider:
            """Handles main agent LLM calls."""
            async def generate(self, messages, system, temperature, max_tokens,
                               tools=None, **kwargs):
                nonlocal call_count
                call_count += 1

                # Manager synthesizing after subtasks complete
                for msg in messages:
                    if isinstance(msg.get("content"), str) and "All subtasks are now complete" in msg["content"]:
                        return make_tool_call("complete_task", {
                            "result": "Market analysis: landscape researched, report written."
                        })

                # Worker agents complete directly
                return make_tool_call("complete_task", {
                    "result": f"Subtask result {call_count}"
                })

        class CompanionProvider:
            """Handles companion (decomposer/planner/evaluator) calls.

            Decomposer: root task gets decompose, subtasks get direct.
            Planner: returns steps matching the approach.
            Evaluator: always PASS.
            """
            async def generate(self, messages, system, temperature, max_tokens,
                               tools=None, **kwargs):
                prompt = messages[0]["content"] if messages else ""

                # Evaluator calls contain "Agent's Result"
                if "Agent's Result" in prompt:
                    return make_text_response("PASS")

                # Decomposer calls contain goal but no "Approach" section
                if "complexity analyst" in system:
                    if "Analyze the market" in prompt:
                        return make_text_response(
                            "DECISION: decompose\n"
                            "Reason: Task has independent research and writing parts"
                        )
                    return make_text_response(
                        "DECISION: direct\n"
                        "Reason: Single focused subtask"
                    )

                # Planner calls contain "Approach" section
                if "planning specialist" in system:
                    if "decompose" in prompt.lower():
                        return make_text_response(
                            "PLAN:\n"
                            "- Research the market landscape\n"
                            "- Write the analysis report\n"
                        )
                    return make_text_response(
                        "PLAN:\n- Complete the task directly"
                    )

                # Fallback
                return make_text_response("PLAN:\n- Do the work")

        def factory(provider_name, model):
            if model == "companion-mock":
                return CompanionProvider()
            return MainProvider()

        config = AgentConfig(
            id="root", name="Root", provider="mock",
            model="mock", system_prompt="Coordinate.",
        )
        companion_config = CompanionConfig(provider="mock", model="companion-mock")
        executor = TaskExecutor(
            provider_factory=factory,
            default_agent_config=config,
            companion_config=companion_config,
            max_turns_per_agent=10,
        )

        task = await executor.submit(
            "Analyze the market",
            "A complete market analysis report",
        )
        await executor.wait_for_completion(task, timeout=30)

        assert task.status == TaskStatus.COMPLETED, f"Got {task.status}: {task.error}"
        # Root task should have been decomposed into 2 subtasks
        assert len(task.subtask_ids) == 2
        # All subtasks should be completed
        for sid in task.subtask_ids:
            st = executor.task_tree.get_task(sid)
            assert st.status == TaskStatus.COMPLETED

        await executor.shutdown()

    asyncio.run(_test())
    print("  PASS: test_planner_auto_decompose")


def test_planner_direct_no_decompose():
    """Test that a direct plan does NOT auto-spawn — agent works normally."""
    async def _test():
        class CompanionProvider:
            async def generate(self, messages, system, temperature, max_tokens,
                               tools=None, **kwargs):
                if "complexity analyst" in system:
                    return make_text_response(
                        "DECISION: direct\nReason: Simple computation"
                    )
                if "planning specialist" in system:
                    return make_text_response(
                        "PLAN:\n- Just compute the answer directly\n"
                    )
                # Evaluator
                return make_text_response("PASS")

        main_provider = MockProvider(responses=[
            make_tool_call("complete_task", {"result": "42"}),
            make_text_response("Done."),
        ])

        def factory(provider_name, model):
            if model == "companion-mock":
                return CompanionProvider()
            return main_provider

        config = AgentConfig(
            id="agent-1", name="Solver", provider="mock",
            model="mock", system_prompt="Solve.",
        )
        companion_config = CompanionConfig(provider="mock", model="companion-mock")
        executor = TaskExecutor(
            provider_factory=factory,
            default_agent_config=config,
            companion_config=companion_config,
        )

        task = await executor.submit("What is 6*7?", "A number")
        await executor.wait_for_completion(task, timeout=10)

        agent = list(executor.agents.values())[0]

        assert task.status == TaskStatus.COMPLETED
        assert task.result == "42"
        # No subtasks spawned — direct approach
        assert len(task.subtask_ids) == 0
        # Plan was injected as context message
        plan_injected = any(
            "Suggested Plan" in str(msg.get("content", ""))
            for msg in agent.message_history
        )
        assert plan_injected, "Direct plan should be injected as context"

        await executor.shutdown()

    asyncio.run(_test())
    print("  PASS: test_planner_direct_no_decompose")


# ── Run all tests ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Unit Tests:")
    test_task_lifecycle()
    test_task_serialization()
    test_task_tree()
    test_bulletin_board()
    test_tool_registry()
    test_agent_config_backward_compat()
    test_prompts_loader()
    test_companion_agent()
    test_agent_companion_registry()
    test_agent_hierarchy()
    test_default_role_is_manager()
    test_parse_decision()
    test_parse_plan()

    print("\nIntegration Tests:")
    test_direct_completion()
    test_decomposition()
    test_subtask_agents_cannot_spawn()
    test_max_turns_limit()
    test_evaluator_pass()
    test_evaluator_fail_then_pass()
    test_evaluator_rejects_incomplete_task()
    test_all_subtask_agents_are_workers()
    test_companion_config_wiring()
    test_planner_auto_decompose()
    test_planner_direct_no_decompose()

    print("\nAll tests passed!")
