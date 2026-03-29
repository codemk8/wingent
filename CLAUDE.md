# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Wingent is a visual workflow editor for multi-agent LLM systems. Users design agent pipelines on a tkinter canvas (drag-and-drop nodes, draw edges), configure each agent's LLM provider/model/prompt, then execute the workflow. Messages flow between agents through async channels.

## Commands

```bash
# Setup (uses local venv at .pyenv/wingent_dev)
source .pyenv/wingent_dev/bin/activate
pip install -r requirements.txt

# Run the GUI application
python simple_canvas.py

# Run tests (no test framework; scripts use assert + print)
python test_core.py
python test_execution.py
python test_ui_workflow.py
```

## Architecture

The codebase has four layers:

- **core** (`wingent/core/`) — Domain models and execution runtime
  - `agent.py`: `AgentConfig` (dataclass), `Agent` (wraps an LLM provider, maintains conversation history, processes messages)
  - `message.py`: `Message` (dataclass), `MessageChannel` (async queue between two agents)
  - `executor.py`: `ExecutionEngine` — initializes agents from a `WorkflowGraph`, creates channels for each edge, runs per-agent async loops that poll channels and route responses

- **app** (`wingent/app/`) — Workflow graph model
  - `workflow.py`: `WorkflowGraph` (nodes + edges), `WorkflowNode` (pairs `AgentConfig` with `VisualPosition`), `WorkflowEdge`. Supports serialization to/from dict, cycle detection, validation

- **providers** (`wingent/providers/`) — LLM provider abstraction
  - `base.py`: `LLMProvider` ABC with `generate()`, `get_available_models()`, `validate_config()`
  - `anthropic.py`, `openai.py`, `local.py`: Concrete implementations

- **ui** (`wingent/ui/`) — Tkinter GUI
  - `canvas.py`: `EnhancedCanvasWidget` — renders workflow graph, handles node drag/drop, right-click context menus, link creation
  - `explorer.py`: `ExplorerPanel` — left sidebar with topology templates tab and agent types palette (drag to canvas)
  - `monitor.py`: `ExecutionMonitor` — right panel showing execution messages and controls
  - `dialogs.py`: Configuration dialogs (agent config, initial message)
  - `styles.py`: Color/font/spacing constants

- **persistence** (`wingent/persistence/serializer.py`) — JSON serialization via `WorkflowSerializer`

- **Entry point**: `simple_canvas.py` — `WingentApp` class wires everything together (menu bar, keyboard shortcuts, file I/O, execution thread management)

## Key Design Patterns

- Execution runs in a daemon thread (`threading.Thread`) calling `asyncio.run()` to bridge tkinter's sync main loop with the async execution engine
- Message routing: `ExecutionEngine._route_message()` checks channels first, falls back to agent inboxes (for initial/external messages)
- Workflow files are JSON; see `examples/research_pipeline.json` for the schema
- Provider is selected per-agent via `AgentConfig.provider` string; `ExecutionEngine._default_provider_factory` does lazy import

## Dependencies

- Python 3.7+ with tkinter (built-in, no pip install needed for UI)
- `anthropic`, `openai` — LLM provider SDKs
- `ollama` — optional, for local models
