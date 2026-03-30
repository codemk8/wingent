"""
Built-in meta-tools for task management and bulletin board coordination.

These tools are automatically available to every agent.
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Optional

from ..tool import Tool, ToolDefinition, ToolParameter
from ..bulletin import BulletinPost, PostType

if TYPE_CHECKING:
    from ..agent import AgentContext


class SpawnSubtaskTool(Tool):
    """Allows an agent to decompose its task by creating subtasks."""

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="spawn_subtask",
            description=(
                "Create a subtask and assign it to a new agent. Use this when "
                "your task is too complex to solve directly and needs to be "
                "broken into smaller pieces. Each subtask will be handled by "
                "a dedicated agent."
            ),
            parameters=[
                ToolParameter(
                    name="goal",
                    type="string",
                    description="What the subtask should accomplish",
                ),
                ToolParameter(
                    name="completion_criteria",
                    type="string",
                    description="How to determine the subtask is done",
                ),
            ],
        )

    async def execute(self, context: AgentContext, goal: str,
                      completion_criteria: str, **kwargs) -> str:
        try:
            subtask = await context.agent_spawner(
                parent_task=context.task,
                subtask_goal=goal,
                subtask_criteria=completion_criteria,
            )
            return (
                f"Subtask created: {subtask.id[:8]}...\n"
                f"Goal: {goal}\n"
                f"A new agent has been assigned and will work on this."
            )
        except Exception as e:
            return f"Failed to create subtask: {e}"


class CompleteTaskTool(Tool):
    """Allows an agent to declare its current task as completed.

    If the agent has an 'evaluator' companion, the result is checked
    against the task goal and completion criteria before being accepted.
    The agent gets up to MAX_EVAL_RETRIES chances to revise its result.
    """

    MAX_EVAL_RETRIES = 2

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="complete_task",
            description=(
                "Declare the current task as completed with a result. "
                "Call this when you have fulfilled the task's goal and "
                "met the completion criteria. Provide the final output."
            ),
            parameters=[
                ToolParameter(
                    name="result",
                    type="string",
                    description="The final result/output of this task",
                ),
            ],
        )

    async def execute(self, context: AgentContext, result: str, **kwargs) -> str:
        # If agent has an evaluator companion, check the result first
        agent = context.agent
        if agent:
            evaluator = agent.get_companion("evaluator")
            if evaluator:
                eval_prompt = (
                    f"## Task Goal\n{context.task.goal}\n\n"
                    f"## Completion Criteria\n{context.task.completion_criteria}\n\n"
                    f"## Agent's Result\n{result}"
                )
                verdict = await evaluator.run(eval_prompt)
                if not verdict.strip().upper().startswith("PASS"):
                    # Rejection — don't mark complete, return feedback to agent
                    reason = verdict.strip()
                    return (
                        f"Evaluation FAILED. Your result did not meet the completion criteria.\n"
                        f"Evaluator feedback: {reason}\n"
                        f"Please revise your work and call complete_task again."
                    )

        context.task.complete(result)

        # Post result to parent's bulletin board if this is a subtask
        if context.task.parent_task_id and context.bulletin_board:
            await context.bulletin_board.post(BulletinPost(
                author_id=context.task.assigned_agent_id or "unknown",
                post_type=PostType.RESULT,
                content=result[:1000],
                references_task_id=context.task.id,
            ))

        return "Task marked as completed."


class PostToBulletinTool(Tool):
    """Allows an agent to post updates to the bulletin board."""

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="post_to_bulletin",
            description=(
                "Post an update to the shared bulletin board. Other agents "
                "working on related tasks can see your posts. Use this to "
                "share progress, ask questions, or report issues."
            ),
            parameters=[
                ToolParameter(
                    name="content",
                    type="string",
                    description="The message to post",
                ),
                ToolParameter(
                    name="post_type",
                    type="string",
                    description="Type of post",
                    required=False,
                    enum=["status_update", "question", "answer", "directive"],
                    default="status_update",
                ),
            ],
        )

    async def execute(self, context: AgentContext, content: str,
                      post_type: str = "status_update", **kwargs) -> str:
        board = context.bulletin_board
        if not board:
            return "No bulletin board available for this task scope."

        await board.post(BulletinPost(
            author_id=context.task.assigned_agent_id or "unknown",
            post_type=PostType(post_type),
            content=content,
            references_task_id=context.task.id,
        ))
        return "Posted to bulletin board."


class ReadBulletinTool(Tool):
    """Allows an agent to read the bulletin board."""

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="read_bulletin",
            description=(
                "Read recent posts from the shared bulletin board to see "
                "what other agents have posted — status updates, results, "
                "questions, or directives from the manager."
            ),
            parameters=[
                ToolParameter(
                    name="post_type",
                    type="string",
                    description="Filter by post type (optional)",
                    required=False,
                    enum=["status_update", "work_item", "claim", "question",
                          "answer", "result", "directive"],
                ),
                ToolParameter(
                    name="limit",
                    type="integer",
                    description="Max number of posts to return (default 20)",
                    required=False,
                    default=20,
                ),
            ],
        )

    async def execute(self, context: AgentContext, post_type: Optional[str] = None,
                      limit: int = 20, **kwargs) -> str:
        board = context.bulletin_board
        if not board:
            return "No bulletin board available for this task scope."

        pt = PostType(post_type) if post_type else None
        posts = board.get_posts(post_type=pt, limit=limit)

        if not posts:
            return "No posts found."

        lines = []
        for post in posts:
            import time
            ts = time.strftime("%H:%M:%S", time.localtime(post.timestamp))
            lines.append(
                f"[{ts}] {post.author_id[:12]} ({post.post_type.value}): "
                f"{post.content[:300]}"
            )
        return "\n".join(lines)
