# Agent Workflow: From Task Submission to Completion

This document describes the complete lifecycle of a task through the Wingent framework, from the moment a user submits it until the final result is returned.

## Overview

```
User submits task
       |
       v
TaskExecutor.submit()
       |
       v
Root Agent created & assigned
       |
       v
  _run_agent_on_task() loop
       |
       v
  Agent.run_turn()  <----+
       |                 |
       v                 |
  LLM decides action     |
       |                 |
    +--+--+              |
    |     |              |
    v     v              |
  tool  text             |
  call  response         |
    |     |              |
    v     |              |
 execute  |              |
  tool    |              |
    |     |              |
    +--+--+              |
       |                 |
       v                 |
  task terminal? ---No---+
       |
      Yes
       |
       v
  Result returned
```

## Step-by-Step Walkthrough

### 1. Task Submission

The user provides a goal and optionally a working directory through the landing page. The server creates a `Task` object and a root `AgentConfig`.

**Key code:** `wingent/server/routes/tasks.py` -> `submit_task()`

```
Task {
    id: "abc123",
    goal: "Analyze the codebase and summarize the architecture",
    completion_criteria: "Complete the task thoroughly and report the result.",
    status: PENDING,
    parent_task_id: None       # root task
}
```

The server builds the root agent's system prompt, which includes:
- General instructions (solve directly or decompose)
- Working directory context (if provided)

### 2. Executor Initialization

`TaskExecutor.submit()` does the following:

1. Adds the task to the `TaskTree`
2. Creates a root `Agent` with:
   - The LLM provider (Anthropic/OpenAI/Local)
   - A `ToolRegistry` containing 4 meta-tools:
     - `spawn_subtask` — decompose into subtasks
     - `complete_task` — declare task done with a result
     - `post_to_bulletin` — post to the shared bulletin board
     - `read_bulletin` — read bulletin board posts
   - Any domain tools registered via `tool_factories`
3. Sets task status to `IN_PROGRESS`
4. Starts `_run_agent_on_task()` as an async task

**Key code:** `wingent/core/executor.py` -> `submit()`, `_create_agent()`

### 3. The Agent Turn Loop

`_run_agent_on_task()` runs a loop calling `agent.run_turn(context)` until the task reaches a terminal state (`COMPLETED` or `FAILED`) or the turn limit is hit.

Each turn, the agent receives an `AgentContext`:
```
AgentContext {
    task:            the current Task object
    bulletin_board:  the parent's board (None for root)
    task_tree:       the global TaskTree (for reading lineage, subtask status)
    agent_spawner:   callback to create subtasks
}
```

**Key code:** `wingent/core/executor.py` -> `_run_agent_on_task()`

### 4. Inside a Single Turn (`Agent.run_turn`)

A turn is the agent's chance to think and act. It contains an inner **tool-use loop** that may involve multiple LLM calls.

#### 4a. Build Context

The agent constructs:

- **System prompt** — assembled from:
  - The agent's base `system_prompt`
  - Current role (worker or manager)
  - Current task goal and completion criteria
  - Subtask status summaries (if task is decomposed)
  - Bulletin board summary (if available)
  - Task hierarchy (lineage from root to current)

- **User message** — on the first turn only, the task description is injected as the opening user message

- **Tool schemas** — all registered tools are serialized to JSON Schema for the LLM

#### 4b. Call the LLM

The agent sends the full conversation history + system prompt + tool schemas to the LLM provider.

The LLM returns one of two `stop_reason` values:

| stop_reason | Meaning | What happens next |
|-------------|---------|-------------------|
| `tool_use` | LLM wants to call one or more tools | Execute tools, feed results back, loop |
| `end_turn` | LLM produced a text response | Append to history, return from turn |

#### 4c. Tool Execution (if `tool_use`)

For each tool call in the response:

1. The tool call (name + input) is appended to history as an assistant message
2. The framework looks up the tool in the `ToolRegistry`
3. The tool's `execute()` method is called with the `AgentContext` + input args
4. The result string is appended to history as a user message (tool_result)
5. The loop continues — the LLM sees the tool results and decides what to do next

This inner loop runs up to 20 rounds per turn.

#### 4d. Turn Result

When the LLM stops calling tools (or the loop limit is hit), the turn returns a `TurnResult`:

```
TurnResult {
    content:          text response (if any)
    tool_calls_made:  total tools called this turn
    task_completed:   True if complete_task was called
    subtasks_spawned: number of spawn_subtask calls
    usage:            cumulative token counts
}
```

**Key code:** `wingent/core/agent.py` -> `run_turn()`

### 5. Decision Point: Direct Completion vs. Decomposition

After each turn, the executor checks the task status:

#### Path A: Direct Completion

The LLM called `complete_task(result="...")` during the turn.

1. `CompleteTaskTool.execute()` sets `task.status = COMPLETED` and `task.result = "..."`
2. If this is a subtask, posts a `RESULT` to the parent's bulletin board
3. The turn loop in `_run_agent_on_task()` sees `task.is_terminal() == True` and exits
4. The async task completes

#### Path B: Decomposition

The LLM called `spawn_subtask(goal="...", completion_criteria="...")` one or more times.

1. Each call triggers `TaskExecutor._spawn_agent_for_subtask()`:
   - Creates a child `Task` (with `parent_task_id` set)
   - Creates a `BulletinBoard` for the parent task (first time only)
   - Sets parent task status to `DECOMPOSED`
   - Posts a `WORK_ITEM` to the bulletin board
   - Creates a new `Agent` (inherits provider/model from parent)
   - Subscribes the new agent to the parent's bulletin board
   - Starts `_run_agent_on_task()` for the child (runs concurrently)

2. The parent agent transitions to **manager mode**

**Key code:** `wingent/core/executor.py` -> `_spawn_agent_for_subtask()`

### 6. Manager Mode

When a task is decomposed, the executor calls `_manager_loop()` for the parent agent.

The manager:
1. Subscribes to its own bulletin board
2. Waits for posts (5-second timeout per poll)
3. On each poll cycle:
   - If `all_subtasks_complete()` is True:
     - Injects a message: "All subtasks are now complete. Synthesize the results."
     - Runs one more agent turn so the LLM can read all subtask results and call `complete_task`
   - If a `QUESTION` or `STATUS_UPDATE` post arrives:
     - Injects the post content as a context message
     - Runs an agent turn so the LLM can respond (post a `DIRECTIVE`, spawn more subtasks, etc.)
   - If a `RESULT` post arrives:
     - Continues to next iteration (checks if all done)

**Key code:** `wingent/core/executor.py` -> `_manager_loop()`

### 7. Subtask Execution

Each subtask agent runs independently through the same `_run_agent_on_task()` loop. A subtask agent can itself decompose further (up to `max_depth`), creating a recursive tree.

When a subtask completes:
1. `complete_task` is called -> task marked COMPLETED
2. A `RESULT` post is published to the parent's bulletin board
3. The parent's manager loop is notified

### 8. Result Bubbling

Completion propagates up the tree:

```
Subtask A completes -> posts RESULT to Board
Subtask B completes -> posts RESULT to Board
                            |
                            v
            Manager sees all_subtasks_complete() == True
                            |
                            v
            Manager LLM synthesizes results
                            |
                            v
            Manager calls complete_task(synthesized_result)
                            |
                            v
            Root task is COMPLETED
```

If this parent is itself a subtask, the same bubbling repeats one level up.

### 9. Completion

The root task reaches a terminal state. The `TaskExecutor.wait_for_completion()` poll detects this. The frontend receives the final `task_completed` event via WebSocket and displays the result.

## Safety Guards

| Guard | Default | What happens |
|-------|---------|-------------|
| `max_turns_per_agent` | 20 | Task fails with "Max turns exceeded" |
| `max_depth` | 3 | `spawn_subtask` returns an error; agent must solve directly |
| `max_agents` | 10 | `spawn_subtask` returns an error; agent must wait or solve directly |
| `wait_for_completion` timeout | caller-defined | Task fails with "Timed out" |

## Sequence Diagram: Full Lifecycle

```
User         Server        Executor       Root Agent      LLM         Subtask Agent
  |              |              |              |            |              |
  |--submit----->|              |              |            |              |
  |              |--submit()--->|              |            |              |
  |              |              |--create------>|            |              |
  |              |              |--run_task---->|            |              |
  |              |              |              |--turn------>|              |
  |              |              |              |            |              |
  |              |              |              |<--spawn-----|              |
  |              |              |              |  subtask    |              |
  |              |              |<--spawn-------|            |              |
  |              |              |--create+run---------------------------->|
  |              |              |              |            |              |
  |              |              | manager_loop |            |     run_turn |
  |              |              |<---board--------------------------result|
  |              |              |              |            |              |
  |              |              |--all done--->|            |              |
  |              |              |              |--turn------>|              |
  |              |              |              |<-complete---|              |
  |              |              |              |  _task      |              |
  |<--result-----|<--complete---|<-------------|            |              |
```
