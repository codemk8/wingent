#!/usr/bin/env python3
"""
Wingent - Agent Framework Visual Editor
"""

import tkinter as tk
from tkinter import filedialog, messagebox
import asyncio
import uuid
import time

from wingent.app.workflow import WorkflowGraph, WorkflowNode, WorkflowEdge
from wingent.core.agent import AgentConfig, VisualPosition
from wingent.core.message import Message
from wingent.core.executor import ExecutionEngine
from wingent.ui.canvas import EnhancedCanvasWidget
from wingent.ui.monitor import ExecutionMonitor
from wingent.ui.dialogs import InitialMessageDialog
from wingent.ui.explorer import ExplorerPanel
from wingent.persistence.serializer import WorkflowSerializer


class WingentApp:
    """Main application window."""

    def __init__(self, root):
        """Initialize application."""
        self.root = root
        self.root.title("Wingent - Agent Framework")
        self.root.geometry("1400x900")
        self.root.configure(bg="#F8FAFC")

        # Workflow
        self.workflow = WorkflowGraph()
        self.workflow.metadata = {"name": "Untitled Workflow", "version": "1.0"}

        # Execution
        self.executor: ExecutionEngine = None
        self.execution_task = None

        # Current file
        self.current_file = None

        # Create UI
        self._create_menu()
        self._create_widgets()

        # Create default workflow
        self._create_default_workflow()

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _create_menu(self):
        """Create menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)

        file_menu.add_command(label="New", command=self._on_new, accelerator="Ctrl+N")
        file_menu.add_command(label="Open...", command=self._on_open, accelerator="Ctrl+O")
        file_menu.add_separator()
        file_menu.add_command(label="Save", command=self._on_save, accelerator="Ctrl+S")
        file_menu.add_command(label="Save As...", command=self._on_save_as, accelerator="Ctrl+Shift+S")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_closing)

        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)

        edit_menu.add_command(label="Add Agent", command=self._on_add_agent, accelerator="Ctrl+A")
        edit_menu.add_command(label="Add Link", command=self._on_add_link, accelerator="Ctrl+L")

        # Run menu
        run_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Run", menu=run_menu)

        run_menu.add_command(label="Start Execution", command=self._on_start_execution, accelerator="F5")
        run_menu.add_command(label="Stop Execution", command=self._on_stop_execution, accelerator="F6")

        # Bind keyboard shortcuts
        self.root.bind("<Control-n>", lambda e: self._on_new())
        self.root.bind("<Control-o>", lambda e: self._on_open())
        self.root.bind("<Control-s>", lambda e: self._on_save())
        self.root.bind("<Control-Shift-S>", lambda e: self._on_save_as())
        self.root.bind("<Control-a>", lambda e: self._on_add_agent())
        self.root.bind("<Control-l>", lambda e: self._on_add_link())
        self.root.bind("<F5>", lambda e: self._on_start_execution())
        self.root.bind("<F6>", lambda e: self._on_stop_execution())

    def _create_widgets(self):
        """Create main widgets."""
        # Main container with modern background
        main_container = tk.Frame(self.root, bg="#F8FAFC")
        main_container.pack(fill=tk.BOTH, expand=True)

        # Split: Explorer (left) | Canvas (center) | Monitor (right)

        # Explorer panel frame with border
        explorer_outer = tk.Frame(main_container, bg="#CBD5E1", padx=1, pady=1, width=302)
        explorer_outer.pack(side=tk.LEFT, fill=tk.BOTH, padx=(10, 5), pady=10)
        explorer_outer.pack_propagate(False)

        explorer_frame = tk.Frame(explorer_outer, width=300, bg="#FFFFFF")
        explorer_frame.pack(fill=tk.BOTH, expand=True)
        explorer_frame.pack_propagate(False)

        # Explorer panel
        self.explorer = ExplorerPanel(
            explorer_frame,
            on_add_template=self._on_add_template,
            on_drag_agent_type=self._on_drag_agent_type
        )
        self.explorer.pack(fill=tk.BOTH, expand=True)

        # Canvas frame with subtle border
        canvas_outer = tk.Frame(main_container, bg="#CBD5E1", padx=1, pady=1)
        canvas_outer.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 5), pady=10)

        canvas_frame = tk.Frame(canvas_outer, bg="#FFFFFF")
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        # Canvas title with modern header
        canvas_title = tk.Frame(canvas_frame, bg="#0F172A", height=40)
        canvas_title.pack(side=tk.TOP, fill=tk.X)
        canvas_title.pack_propagate(False)

        tk.Label(
            canvas_title,
            text="Workflow Editor",
            font=("Segoe UI", 11, "bold"),
            fg="#F8FAFC",
            bg="#0F172A"
        ).pack(side=tk.LEFT, padx=15, pady=8)

        # Canvas
        self.canvas = EnhancedCanvasWidget(canvas_frame, self.workflow)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Set callbacks
        self.canvas.on_graph_changed = self._on_graph_changed
        self.canvas.on_node_changed = self._on_node_changed

        # Monitor frame with border
        monitor_outer = tk.Frame(main_container, bg="#CBD5E1", padx=1, pady=1, width=452)
        monitor_outer.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(5, 10), pady=10)
        monitor_outer.pack_propagate(False)

        monitor_frame = tk.Frame(monitor_outer, width=450, bg="#FFFFFF")
        monitor_frame.pack(fill=tk.BOTH, expand=True)
        monitor_frame.pack_propagate(False)

        # Monitor
        self.monitor = ExecutionMonitor(
            monitor_frame,
            on_start=self._on_start_execution,
            on_stop=self._on_stop_execution
        )
        self.monitor.pack(fill=tk.BOTH, expand=True)

        # Status bar with modern styling
        status_outer = tk.Frame(self.root, bg="#CBD5E1", height=32)
        status_outer.pack(side=tk.BOTTOM, fill=tk.X)
        status_outer.pack_propagate(False)

        self.status_bar = tk.Label(
            status_outer,
            text="Ready",
            anchor=tk.W,
            font=("Segoe UI", 9),
            bg="#F8FAFC",
            fg="#475569",
            padx=15,
            pady=6
        )
        self.status_bar.pack(fill=tk.BOTH, expand=True)

    def _create_default_workflow(self):
        """Create a default workflow with 3 agents."""
        # Agent 1: Researcher
        agent1 = AgentConfig(
            id="researcher",
            name="Researcher",
            provider="anthropic",
            model="claude-sonnet-4-5-20250929",
            system_prompt="You are a research assistant. Analyze questions and provide well-researched insights.",
            temperature=0.7,
            max_tokens=1000
        )
        node1 = WorkflowNode(agent1, VisualPosition(100, 150))
        self.workflow.add_node(node1)

        # Agent 2: Writer
        agent2 = AgentConfig(
            id="writer",
            name="Writer",
            provider="anthropic",
            model="claude-sonnet-4-5-20250929",
            system_prompt="You are a writer. Take research and create clear, concise summaries.",
            temperature=0.8,
            max_tokens=1000
        )
        node2 = WorkflowNode(agent2, VisualPosition(400, 150))
        self.workflow.add_node(node2)

        # Agent 3: Editor
        agent3 = AgentConfig(
            id="editor",
            name="Editor",
            provider="anthropic",
            model="claude-3-5-haiku-20241022",
            system_prompt="You are an editor. Review and refine written content for clarity and impact.",
            temperature=0.6,
            max_tokens=800
        )
        node3 = WorkflowNode(agent3, VisualPosition(700, 150))
        self.workflow.add_node(node3)

        # Links
        self.workflow.add_edge(WorkflowEdge("researcher", "writer"))
        self.workflow.add_edge(WorkflowEdge("writer", "editor"))

        # Redraw
        self.canvas.draw_graph()

        self._update_status("Default workflow created")

    def _on_graph_changed(self):
        """Handle graph change."""
        errors = self.workflow.validate()
        if errors:
            self._update_status(f"Warning: {errors[0]}")
        else:
            self._update_status(f"Workflow: {len(self.workflow.nodes)} agents, {len(self.workflow.edges)} links")

    def _on_node_changed(self, node_id: str, config: AgentConfig):
        """Handle node configuration change."""
        self._update_status(f"Updated agent: {config.name}")

    def _update_status(self, message: str):
        """Update status bar."""
        self.status_bar.config(text=message)

    # File operations

    def _on_new(self):
        """Create new workflow."""
        if messagebox.askyesno("New Workflow", "Create a new workflow? Current workflow will be cleared."):
            self.workflow = WorkflowGraph()
            self.workflow.metadata = {"name": "Untitled Workflow", "version": "1.0"}
            self.canvas.workflow = self.workflow
            self.canvas.draw_graph()
            self.current_file = None
            self._update_status("New workflow created")

    def _on_open(self):
        """Open workflow from file."""
        filename = filedialog.askopenfilename(
            title="Open Workflow",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if filename:
            try:
                self.workflow = WorkflowSerializer.from_json(filename)
                self.canvas.workflow = self.workflow
                self.canvas.draw_graph()
                self.current_file = filename
                self._update_status(f"Opened: {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open workflow:\n{e}")

    def _on_save(self):
        """Save workflow."""
        if self.current_file:
            self._save_to_file(self.current_file)
        else:
            self._on_save_as()

    def _on_save_as(self):
        """Save workflow as new file."""
        filename = filedialog.asksaveasfilename(
            title="Save Workflow",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if filename:
            self._save_to_file(filename)

    def _save_to_file(self, filename: str):
        """Save workflow to file."""
        try:
            WorkflowSerializer.to_json(self.workflow, filename)
            self.current_file = filename
            self._update_status(f"Saved: {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save workflow:\n{e}")

    # Edit operations

    def _on_add_agent(self):
        """Add new agent."""
        # Get center of canvas
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        x = canvas_width // 2 if canvas_width > 0 else 400
        y = canvas_height // 2 if canvas_height > 0 else 300

        self.canvas._add_new_node(x, y)

    def _on_add_template(self, template: dict):
        """
        Add a topology template to the canvas.

        Args:
            template: Template data with agents and edges
        """
        # Clear current workflow
        if messagebox.askyesno("Load Template",
                               f"Load '{template['name']}' template?\n\nThis will replace the current workflow."):
            # Create new workflow
            self.workflow = WorkflowGraph()
            self.workflow.metadata = {"name": template["name"], "version": "1.0"}
            self.canvas.workflow = self.workflow

            # Create agents
            agent_id_map = {}  # Map template index to actual agent ID
            for idx, agent_data in enumerate(template["agents"]):
                agent_id = f"agent_{uuid.uuid4().hex[:8]}"
                agent_id_map[f"agent_{idx}"] = agent_id

                config = AgentConfig(
                    id=agent_id,
                    name=agent_data["name"],
                    provider=agent_data["provider"],
                    model=agent_data["model"],
                    system_prompt=agent_data["prompt"],
                    temperature=0.7,
                    max_tokens=1000
                )

                node = WorkflowNode(
                    config,
                    VisualPosition(agent_data["x"], agent_data["y"])
                )
                self.workflow.add_node(node)

            # Create edges
            for source_idx, target_idx in template.get("edges", []):
                source_id = agent_id_map[source_idx]
                target_id = agent_id_map[target_idx]
                self.workflow.add_edge(WorkflowEdge(source_id, target_id))

            # Redraw
            self.canvas.draw_graph()
            self._update_status(f"Loaded template: {template['name']}")

    def _on_drag_agent_type(self, agent_type: dict, x_root: int, y_root: int):
        """
        Handle agent type drag-and-drop.

        Args:
            agent_type: Agent type data
            x_root: Screen X coordinate
            y_root: Screen Y coordinate
        """
        # Convert screen coordinates to canvas coordinates
        canvas_x = x_root - self.canvas.winfo_rootx()
        canvas_y = y_root - self.canvas.winfo_rooty()

        # Check if drop is within canvas bounds
        if (0 <= canvas_x <= self.canvas.winfo_width() and
            0 <= canvas_y <= self.canvas.winfo_height()):
            # Add agent at drop location
            self.canvas.add_agent_from_type(agent_type, canvas_x, canvas_y)
            self._update_status(f"Added {agent_type['name']} to canvas")

    def _on_add_link(self):
        """Add link between agents."""
        messagebox.showinfo(
            "Add Link",
            "To add a link:\n\n1. Right-click on the source agent\n2. Select 'Create Link From Here'\n3. Click on the target agent"
        )

    # Execution operations

    def _on_start_execution(self):
        """Start workflow execution."""
        if not self.workflow.nodes:
            messagebox.showwarning("Empty Workflow", "Add some agents first!")
            return

        # Validate workflow
        errors = self.workflow.validate()
        if errors:
            messagebox.showerror("Invalid Workflow", f"Cannot execute:\n\n" + "\n".join(errors))
            return

        # Get initial message
        agent_names = [node.agent_config.id for node in self.workflow.nodes.values()]
        dialog = InitialMessageDialog(self.root, agent_names)
        self.root.wait_window(dialog)

        if not dialog.result:
            return  # User cancelled

        # Create initial message
        initial_message = Message(
            id=str(uuid.uuid4()),
            sender_id="user",
            recipient_id=dialog.result["recipient"],
            content=dialog.result["content"],
            timestamp=time.time(),
            metadata={}
        )

        # Start execution
        self._start_execution_async(initial_message)

    def _start_execution_async(self, initial_message: Message):
        """Start async execution."""
        # Create executor
        self.executor = ExecutionEngine(self.workflow)

        # Add message callback
        self.executor.add_message_callback(lambda msg: self.monitor.add_message(msg))

        # Update UI
        self.monitor.set_running(True)
        self._update_status("Initializing execution...")

        # Run in background
        async def run():
            try:
                await self.executor.initialize()
                self._update_status("Execution running...")

                await self.executor.start([initial_message])

            except Exception as e:
                print(f"Execution error: {e}")
                import traceback
                traceback.print_exc()
                error_msg = str(e)
                self.root.after(0, lambda msg=error_msg: messagebox.showerror("Execution Error", msg))
            finally:
                self.root.after(0, lambda: self.monitor.set_running(False))
                self.root.after(0, lambda: self._update_status("Execution stopped"))

        # Start in thread (for async)
        import threading

        def run_async():
            asyncio.run(run())

        self.execution_task = threading.Thread(target=run_async, daemon=True)
        self.execution_task.start()

    def _on_stop_execution(self):
        """Stop workflow execution."""
        if self.executor:
            async def stop():
                await self.executor.stop()

            # Run stop
            asyncio.run(stop())

            self.executor = None
            self.monitor.set_running(False)
            self._update_status("Execution stopped")

    def _on_closing(self):
        """Handle window close."""
        # Stop execution if running
        if self.executor and self.executor.running:
            if messagebox.askyesno("Execution Running", "Stop execution and exit?"):
                self._on_stop_execution()
            else:
                return

        self.root.destroy()


def main():
    """Run the application."""
    print("Starting Wingent - Agent Framework")

    root = tk.Tk()
    app = WingentApp(root)

    print("Application initialized")
    print("\nUsage:")
    print("  - Double-click agents to configure")
    print("  - Right-click for context menu")
    print("  - Drag agents to move them")
    print("  - Use Run > Start Execution to run the workflow")

    root.mainloop()


if __name__ == "__main__":
    main()
