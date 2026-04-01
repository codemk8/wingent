"""
Session — persistent root agent across multiple tasks.
"""

from typing import Dict, Any, Optional, List, Callable
import asyncio
import uuid

from .task import Task, TaskStatus, TaskTree
from .bulletin import BulletinBoard, BulletinPost, PostType
from .tool import Tool, ToolRegistry
from .agent import Agent, AgentConfig, AgentContext, AgentRole, CompanionAgent, CompanionConfig
from .tools.meta import SpawnSubtaskTool, CompleteTaskTool, PostToBulletinTool, ReadBulletinTool
from .prompts import get_manager_prompt, get_worker_prompt, get_companion_prompt


class Session:
    """A session with a persistent root agent that handles multiple tasks.

    The root agent retains its message history across tasks, giving it
    context from earlier work in the session.

    Usage:
        session = Session(provider_factory=my_factory, agent_config=config)
        task = await session.submit("Write a report", "A 2000-word report")
        await session.wait_for_completion(task, timeout=300)
        print(task.result)

        # Later — same root agent, with context from the first task
        task2 = await session.submit("Now summarize it", "A 3-sentence summary")
        await session.wait_for_completion(task2, timeout=60)
    """

    def __init__(
        self,
        provider_factory: Callable,
        agent_config: AgentConfig,
        tool_factories: Optional[Dict[str, Callable[[], Tool]]] = None,
        max_agents: int = 10,
        max_turns_per_agent: int = 20,
        working_directory: Optional[str] = None,
        companion_config: Optional[CompanionConfig] = None,
    ):
        self.id = str(uuid.uuid4())
        self.provider_factory = provider_factory
        self.agent_config = agent_config
        self.tool_factories = tool_factories or {}
        self.max_agents = max_agents
        self.max_turns_per_agent = max_turns_per_agent
        self.working_directory = working_directory
        self.companion_config = companion_config

        self.task_tree = TaskTree()
        self.boards: Dict[str, BulletinBoard] = {}
        self.agents: Dict[str, Agent] = {}
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._callbacks: List[Callable] = []
        self._agent_count = 0
        self.tasks: List[Task] = []

        # Create the persistent root agent
        self.root_agent = self._create_agent(agent_config)

    def add_callback(self, callback: Callable) -> None:
        self._callbacks.append(callback)

    def _notify(self, event: str, data: Dict[str, Any]) -> None:
        for cb in self._callbacks:
            try:
                cb(event, data)
            except Exception:
                pass

    async def submit(self, goal: str, completion_criteria: str) -> Task:
        """Submit a task to the session's root agent."""
        task = Task(goal=goal, completion_criteria=completion_criteria)
        self.task_tree.add_task(task)
        self.tasks.append(task)

        task.assigned_agent_id = self.root_agent.config.id
        task.status = TaskStatus.IN_PROGRESS

        self._notify("task_started", {
            "task_id": task.id,
            "agent_id": self.root_agent.config.id,
        })

        self._running_tasks[task.id] = asyncio.create_task(
            self._run_agent_on_task(self.root_agent, task)
        )
        return task

    async def _run_agent_on_task(self, agent: Agent, task: Task) -> None:
        """Core loop: run agent turns until the task is terminal."""
        agent.current_task_id = task.id

        parent_board = None
        if task.parent_task_id:
            parent_board = self.boards.get(task.parent_task_id)

        context = AgentContext(
            task=task,
            bulletin_board=parent_board,
            task_tree=self.task_tree,
            agent_spawner=self._spawn_subtask,
            agent=agent,
        )

        # Let companions analyze the task (decomposer → planner)
        plan = await agent.prepare_for_task(task)

        if plan.approach == "decompose" and plan.steps:
            for step in plan.steps:
                try:
                    await self._spawn_subtask(
                        parent_task=task,
                        subtask_goal=step,
                        subtask_criteria=f"Complete this step: {step}",
                    )
                except RuntimeError:
                    break
            if task.status == TaskStatus.DECOMPOSED:
                await self._manager_loop(agent, task)
                return

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
            post = await board.wait_for_post(manager.config.id, timeout=5.0)

            if self.task_tree.all_subtasks_complete(task.id):
                manager.add_context_message(
                    "All subtasks are now complete. Review the results and "
                    "call complete_task with the synthesized final result."
                )
                context = AgentContext(
                    task=task,
                    bulletin_board=board,
                    task_tree=self.task_tree,
                    agent_spawner=self._spawn_subtask,
                    agent=manager,
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
                if post.post_type == PostType.RESULT:
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
                        agent_spawner=self._spawn_subtask,
                        agent=manager,
                    )
                    await manager.run_turn(context)
                    turns += 1

        if not task.is_terminal():
            task.fail("Manager max turns exceeded")

    async def _spawn_subtask(
        self,
        parent_task: Task,
        subtask_goal: str,
        subtask_criteria: str,
        agent_config: Optional[AgentConfig] = None,
    ) -> Task:
        """Create a subtask with a worker agent."""
        if self._agent_count >= self.max_agents:
            raise RuntimeError(
                f"Max agent limit ({self.max_agents}) reached. "
                "Complete existing tasks before spawning new agents."
            )

        subtask = Task(
            goal=subtask_goal,
            completion_criteria=subtask_criteria,
            parent_task_id=parent_task.id,
        )
        self.task_tree.add_task(subtask)
        parent_task.subtask_ids.append(subtask.id)

        if parent_task.id not in self.boards:
            self.boards[parent_task.id] = BulletinBoard(parent_task.id)
            parent_task.status = TaskStatus.DECOMPOSED

        board = self.boards[parent_task.id]

        await board.post(BulletinPost(
            author_id=parent_task.assigned_agent_id or "system",
            post_type=PostType.WORK_ITEM,
            content=subtask_goal,
            references_task_id=subtask.id,
        ))

        config = agent_config or self._derive_worker_config(parent_task)
        parent_agent = self.agents.get(parent_task.assigned_agent_id or "")
        parent_level = parent_agent.level if parent_agent else 0
        agent = self._create_agent(config, level=parent_level + 1, parent=parent_agent)
        agent.role = AgentRole.WORKER
        subtask.assigned_agent_id = agent.config.id
        subtask.status = TaskStatus.IN_PROGRESS

        board.subscribe(agent.config.id)

        self._notify("subtask_spawned", {
            "parent_task_id": parent_task.id,
            "subtask_id": subtask.id,
            "agent_id": agent.config.id,
            "goal": subtask_goal,
        })

        self._running_tasks[subtask.id] = asyncio.create_task(
            self._run_agent_on_task(agent, subtask)
        )
        return subtask

    def _create_agent(self, config: AgentConfig, level: int = 0,
                      parent: Optional[Agent] = None) -> Agent:
        """Create an Agent instance with provider and tools."""
        provider = self.provider_factory(config.provider, config.model)
        registry = ToolRegistry()

        for tool_name in config.tool_names:
            if tool_name in self.tool_factories:
                registry.register(self.tool_factories[tool_name]())

        registry.register(SpawnSubtaskTool())
        registry.register(CompleteTaskTool())
        registry.register(PostToBulletinTool())
        registry.register(ReadBulletinTool())

        agent = Agent(config, provider, registry, level=level, parent=parent)

        if self.companion_config:
            cc = self.companion_config
            for purpose in ("evaluator", "decomposer", "planner"):
                companion_provider = self.provider_factory(cc.provider, cc.model)
                agent.add_companion(CompanionAgent(
                    purpose=purpose,
                    system_prompt=get_companion_prompt(purpose),
                    provider=companion_provider,
                    config=cc,
                ))

        self.agents[config.id] = agent
        self._agent_count += 1
        return agent

    def _derive_worker_config(self, parent_task: Task) -> AgentConfig:
        """Generate a worker AgentConfig for a subtask."""
        base = self.agents.get(parent_task.assigned_agent_id or "")
        cfg = base.config if base else self.agent_config
        if not cfg:
            raise RuntimeError("Cannot derive agent config")

        return AgentConfig(
            id=str(uuid.uuid4()),
            name=f"Worker-{uuid.uuid4().hex[:8]}",
            provider=cfg.provider,
            model=cfg.model,
            system_prompt=get_worker_prompt(self.working_directory),
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
            tool_names=cfg.tool_names,
            can_spawn=False,
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
