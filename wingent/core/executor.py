"""
Task executor — drives hierarchical agent execution.
"""

from typing import Dict, Any, Optional, List, Callable
import asyncio
import uuid

from .task import Task, TaskStatus, TaskTree
from .bulletin import BulletinBoard, BulletinPost, PostType
from .tool import Tool, ToolRegistry
from .agent import Agent, AgentConfig, AgentContext, AgentRole
from .tools.meta import SpawnSubtaskTool, CompleteTaskTool, PostToBulletinTool, ReadBulletinTool
from .prompts import get_manager_prompt, get_worker_prompt


class TaskExecutor:
    """Drives the execution of a hierarchical task tree.

    Usage:
        executor = TaskExecutor(provider_factory=my_factory)
        task = await executor.submit("Write a report", "A 2000-word report")
        await executor.wait_for_completion(task, timeout=300)
        print(task.result)
    """

    def __init__(
        self,
        provider_factory: Callable,
        default_agent_config: Optional[AgentConfig] = None,
        tool_factories: Optional[Dict[str, Callable[[], Tool]]] = None,
        max_depth: int = 3,
        max_agents: int = 10,
        max_turns_per_agent: int = 20,
        working_directory: Optional[str] = None,
    ):
        self.provider_factory = provider_factory
        self.default_agent_config = default_agent_config
        self.tool_factories = tool_factories or {}
        self.max_depth = max_depth
        self.max_agents = max_agents
        self.max_turns_per_agent = max_turns_per_agent
        self._working_directory = working_directory

        self.task_tree = TaskTree()
        self.boards: Dict[str, BulletinBoard] = {}
        self.agents: Dict[str, Agent] = {}
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._callbacks: List[Callable] = []
        self._agent_count = 0

    def add_callback(self, callback: Callable) -> None:
        self._callbacks.append(callback)

    def _notify(self, event: str, data: Dict[str, Any]) -> None:
        for cb in self._callbacks:
            try:
                cb(event, data)
            except Exception:
                pass

    async def submit(
        self,
        goal: str,
        completion_criteria: str,
        agent_config: Optional[AgentConfig] = None,
    ) -> Task:
        """Create a root task and assign an agent to work on it."""
        task = Task(goal=goal, completion_criteria=completion_criteria)
        self.task_tree.add_task(task)

        config = agent_config or self.default_agent_config
        if not config:
            raise ValueError("No agent config provided and no default set")

        agent = self._create_agent(config)
        task.assigned_agent_id = agent.config.id
        task.status = TaskStatus.IN_PROGRESS

        self._notify("task_started", {"task_id": task.id, "agent_id": agent.config.id})

        self._running_tasks[task.id] = asyncio.create_task(
            self._run_agent_on_task(agent, task)
        )
        return task

    async def _run_agent_on_task(self, agent: Agent, task: Task) -> None:
        """Core loop: run agent turns until the task is terminal."""
        agent.current_task_id = task.id

        # Determine which bulletin board this agent can see:
        # If this is a subtask, it can see the parent's board
        parent_board = None
        if task.parent_task_id:
            parent_board = self.boards.get(task.parent_task_id)

        context = AgentContext(
            task=task,
            bulletin_board=parent_board,
            task_tree=self.task_tree,
            agent_spawner=self._spawn_agent_for_subtask,
        )

        turns = 0
        while not task.is_terminal() and turns < self.max_turns_per_agent:
            try:
                turn_result = await agent.run_turn(context)
                turns += 1

                self._notify("turn_completed", {
                    "task_id": task.id,
                    "agent_id": agent.config.id,
                    "turn": turns,
                    "tool_calls": turn_result.tool_calls_made,
                    "content_preview": turn_result.content[:200] if turn_result.content else "",
                })

                # If task was decomposed, switch to manager mode
                if task.status == TaskStatus.DECOMPOSED:
                    await self._manager_loop(agent, task)
                    return

            except Exception as e:
                task.fail(f"Agent error: {e}")
                self._notify("task_failed", {"task_id": task.id, "error": str(e)})
                return

        if not task.is_terminal():
            task.fail(f"Max turns ({self.max_turns_per_agent}) exceeded")
            self._notify("task_failed", {
                "task_id": task.id,
                "error": "max turns exceeded",
            })

    async def _manager_loop(self, manager: Agent, task: Task) -> None:
        """Monitor bulletin board and synthesize when all subtasks complete."""
        manager.role = AgentRole.MANAGER
        board = self.boards[task.id]
        board.subscribe(manager.config.id)

        self._notify("manager_started", {
            "task_id": task.id,
            "agent_id": manager.config.id,
        })

        turns = 0
        while not task.is_terminal() and turns < self.max_turns_per_agent:
            # Wait for activity
            post = await board.wait_for_post(manager.config.id, timeout=5.0)

            if self.task_tree.all_subtasks_complete(task.id):
                # All done — let manager synthesize
                manager.add_context_message(
                    "All subtasks are now complete. Review the results and "
                    "call complete_task with the synthesized final result."
                )
                context = AgentContext(
                    task=task,
                    bulletin_board=board,
                    task_tree=self.task_tree,
                    agent_spawner=self._spawn_agent_for_subtask,
                )
                await manager.run_turn(context)
                turns += 1

                if task.is_terminal():
                    self._notify("task_completed", {
                        "task_id": task.id,
                        "result_preview": (task.result or "")[:200],
                    })
                    return
            elif post:
                # React to posts if needed (e.g., failures, questions)
                if post.post_type == PostType.RESULT:
                    # A subtask finished — check if all done on next iteration
                    continue
                elif post.post_type in (PostType.QUESTION, PostType.STATUS_UPDATE):
                    manager.add_context_message(
                        f"Bulletin board update from {post.author_id[:12]}: "
                        f"[{post.post_type.value}] {post.content[:500]}"
                    )
                    context = AgentContext(
                        task=task,
                        bulletin_board=board,
                        task_tree=self.task_tree,
                        agent_spawner=self._spawn_agent_for_subtask,
                    )
                    await manager.run_turn(context)
                    turns += 1

        if not task.is_terminal():
            task.fail("Manager max turns exceeded")

    async def _spawn_agent_for_subtask(
        self,
        parent_task: Task,
        subtask_goal: str,
        subtask_criteria: str,
        agent_config: Optional[AgentConfig] = None,
    ) -> Task:
        """Create a subtask, bulletin board, and agent. Start the agent."""
        # Check limits
        depth = self.task_tree.get_depth(parent_task.id)
        if depth >= self.max_depth:
            raise RuntimeError(
                f"Max decomposition depth ({self.max_depth}) reached. "
                "Complete the task directly instead of spawning more subtasks."
            )
        if self._agent_count >= self.max_agents:
            raise RuntimeError(
                f"Max agent limit ({self.max_agents}) reached. "
                "Complete existing tasks before spawning new agents."
            )

        # Create subtask
        subtask = Task(
            goal=subtask_goal,
            completion_criteria=subtask_criteria,
            parent_task_id=parent_task.id,
        )
        self.task_tree.add_task(subtask)
        parent_task.subtask_ids.append(subtask.id)

        # Ensure parent has a bulletin board
        if parent_task.id not in self.boards:
            self.boards[parent_task.id] = BulletinBoard(parent_task.id)
            parent_task.status = TaskStatus.DECOMPOSED

        board = self.boards[parent_task.id]

        # Post work item
        await board.post(BulletinPost(
            author_id=parent_task.assigned_agent_id or "system",
            post_type=PostType.WORK_ITEM,
            content=subtask_goal,
            references_task_id=subtask.id,
        ))

        # Create agent
        config = agent_config or self._derive_agent_config(parent_task, subtask)
        parent_agent = self.agents.get(parent_task.assigned_agent_id or "")
        parent_level = parent_agent.level if parent_agent else 0
        agent = self._create_agent(config, level=parent_level + 1, parent=parent_agent)
        if not config.can_spawn:
            agent.role = AgentRole.WORKER
        subtask.assigned_agent_id = agent.config.id
        subtask.status = TaskStatus.IN_PROGRESS

        # Subscribe to parent's board
        board.subscribe(agent.config.id)

        self._notify("subtask_spawned", {
            "parent_task_id": parent_task.id,
            "subtask_id": subtask.id,
            "agent_id": agent.config.id,
            "goal": subtask_goal,
        })

        # Start agent
        self._running_tasks[subtask.id] = asyncio.create_task(
            self._run_agent_on_task(agent, subtask)
        )
        return subtask

    def _create_agent(self, config: AgentConfig, level: int = 0,
                      parent: Optional[Agent] = None) -> Agent:
        """Create an Agent instance with provider and tools."""
        provider = self.provider_factory(config.provider, config.model)
        registry = ToolRegistry()

        # Register domain tools
        for tool_name in config.tool_names:
            if tool_name in self.tool_factories:
                registry.register(self.tool_factories[tool_name]())

        # Always register meta-tools
        registry.register(SpawnSubtaskTool())
        registry.register(CompleteTaskTool())
        registry.register(PostToBulletinTool())
        registry.register(ReadBulletinTool())

        agent = Agent(config, provider, registry, level=level, parent=parent)
        self.agents[config.id] = agent
        self._agent_count += 1
        return agent

    def _derive_agent_config(self, parent_task: Task, subtask: Task) -> AgentConfig:
        """Generate an AgentConfig for a subtask based on the parent's agent.

        Agents at max_depth - 1 become workers (cannot spawn further).
        All others get the manager prompt and can continue to decompose.
        """
        depth = self.task_tree.get_depth(parent_task.id) + 1
        is_leaf = depth >= self.max_depth - 1

        if is_leaf:
            system_prompt = get_worker_prompt(self._working_directory)
            name = f"Worker-{subtask.id[:8]}"
        else:
            system_prompt = get_manager_prompt(self._working_directory)
            name = f"Agent-{subtask.id[:8]}"

        base = self.agents.get(parent_task.assigned_agent_id or "")
        cfg = base.config if base else self.default_agent_config
        if not cfg:
            raise RuntimeError("Cannot derive agent config: no parent agent or default config")

        return AgentConfig(
            id=str(uuid.uuid4()),
            name=name,
            provider=cfg.provider,
            model=cfg.model,
            system_prompt=system_prompt,
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
            tool_names=cfg.tool_names,
            can_spawn=not is_leaf,
        )

    async def wait_for_completion(self, task: Task, timeout: Optional[float] = None) -> Task:
        """Block until a task reaches terminal state."""
        async def _wait():
            while not task.is_terminal():
                await asyncio.sleep(0.2)
            return task

        if timeout:
            try:
                await asyncio.wait_for(_wait(), timeout=timeout)
            except asyncio.TimeoutError:
                task.fail(f"Timed out after {timeout}s")
        else:
            await _wait()
        return task

    async def shutdown(self) -> None:
        """Cancel all running agent loops."""
        for t in self._running_tasks.values():
            t.cancel()
        await asyncio.gather(*self._running_tasks.values(), return_exceptions=True)
        self._running_tasks.clear()

    def get_statistics(self) -> Dict[str, Any]:
        all_tasks = self.task_tree.all_tasks()
        return {
            "total_tasks": len(all_tasks),
            "completed": sum(1 for t in all_tasks if t.status == TaskStatus.COMPLETED),
            "failed": sum(1 for t in all_tasks if t.status == TaskStatus.FAILED),
            "in_progress": sum(1 for t in all_tasks if t.status == TaskStatus.IN_PROGRESS),
            "decomposed": sum(1 for t in all_tasks if t.status == TaskStatus.DECOMPOSED),
            "total_agents": self._agent_count,
            "bulletin_boards": len(self.boards),
        }
