# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Wingent is a task-oriented multi-agent LLM framework with a web UI. Users submit a goal via a browser-based landing page; the framework dynamically creates and coordinates agents that decompose, execute, and synthesize results. Agents communicate through shared bulletin boards and use tools (including spawning sub-agents) to complete work.

## Commands

```bash
# Backend setup
source .pyenv/wingent_dev/bin/activate
pip install -r requirements.txt

# Run backend (FastAPI)
python -m uvicorn wingent.server.app:app --reload --port 8000

# Run frontend (Vite dev server)
cd frontend && npm install && npm run dev

# Run both via Docker Compose (dev mode with hot-reload)
docker-compose -f docker-compose.dev.yml up

# Run tests (no test framework; scripts use assert + print)
python test_core.py
python test_task_execution.py
```

## Architecture

### Core (`wingent/core/`)

Task-oriented execution runtime:

- `task.py`: `Task` (dataclass with goal, completion_criteria, status lifecycle: PENDING → IN_PROGRESS → DECOMPOSED/COMPLETED/FAILED), `TaskTree` (manages hierarchy, depth, lineage)
- `agent.py`: `AgentConfig` (dataclass), `Agent` (wraps LLM provider, runs tool-use loop in `run_turn()` — call LLM → execute tools → feed results → repeat until done)
- `executor.py`: `TaskExecutor` — submits root tasks, runs agent turn loops, manages subtask spawning, runs manager loop for decomposed tasks
- `bulletin.py`: `BulletinBoard` — async pub/sub per task scope. Post types: STATUS_UPDATE, WORK_ITEM, CLAIM, QUESTION, ANSWER, RESULT, DIRECTIVE
- `tool.py`: `Tool` ABC with `definition()` and `execute()`, `ToolRegistry` for registration and LLM schema serialization
- `tools/meta.py`: Four built-in meta-tools — `spawn_subtask`, `complete_task`, `post_to_bulletin`, `read_bulletin`
- `message.py`: Legacy `Message` / `MessageChannel` (kept for backward compatibility)

### Server (`wingent/server/`)

FastAPI backend:

- `app.py`: FastAPI app with CORS, lifespan, WebSocket endpoint, static file serving for production
- `state.py`: `AppState` singleton — agent configs, executor, WebSocket manager, agent/topology templates, provider-model mappings
- `ws.py`: `WebSocketManager` — bridges TaskExecutor callbacks to browser via WebSocket events
- `routes/agents.py`: CRUD for agent configs, templates, topologies, providers
- `routes/tasks.py`: Task submission (POST /api/tasks), status, stats, stop execution

### Frontend (`frontend/src/`)

React + React Flow + Tailwind CSS (Vite build):

- `App.tsx`: Routes between Landing view and execution view (Sidebar + Canvas + Monitor)
- `store.ts`: Zustand store — agents, tasks, events, WebSocket connection, UI state
- `api.ts`: REST client for all backend endpoints
- `components/Landing.tsx`: Task-first landing page with goal input, optional working directory/provider/model
- `components/Canvas.tsx`: React Flow canvas — agent nodes + dynamic task nodes during execution
- `components/Monitor.tsx`: Task tree, event log, stats, stop/new task controls
- `components/Sidebar.tsx`: Topology templates + agent type palette
- `components/AgentConfigModal.tsx`: Agent configuration modal
- `components/TaskSubmitModal.tsx`: Task submission modal

### Other Layers

- **Providers** (`wingent/providers/`): `LLMProvider` ABC with `generate(tools=...)` supporting function calling. Implementations: `anthropic.py`, `openai.py`, `local.py`
- **App** (`wingent/app/workflow.py`): Legacy `WorkflowGraph` model (kept for backward compatibility)
- **Persistence** (`wingent/persistence/serializer.py`): JSON serialization via `WorkflowSerializer`

## Key Design Patterns

- **Task-oriented execution**: Each task has a goal and termination criteria. Agents either solve directly (call `complete_task`) or decompose (call `spawn_subtask` → become manager)
- **Hierarchical spawning**: Subtask agents run concurrently; parent agent enters manager loop, monitors bulletin board, synthesizes results when all subtasks complete
- **Tool-use loop**: Agent.run_turn() calls LLM with tool schemas → LLM returns tool_use → execute tool → feed result back → loop (up to 20 rounds per turn)
- **Safety guards**: max_turns_per_agent (20), max_depth (3), max_agents (10)
- **Real-time updates**: TaskExecutor fires callbacks → WebSocketManager broadcasts to browser → Zustand store updates React state

## Docker

- `Dockerfile`: Multi-stage build (Node frontend build → Python runtime), serves on port 8000
- `docker-compose.yml`: Production single-service
- `docker-compose.dev.yml`: Dev mode with volume mounts, hot-reload, host filesystem access via HOST_WORKSPACE

## Dependencies

- Python 3.11+, `fastapi`, `uvicorn`
- `anthropic`, `openai` — LLM provider SDKs
- `ollama` — optional, for local models
- Node 20+, React, React Flow, Zustand, Tailwind CSS
