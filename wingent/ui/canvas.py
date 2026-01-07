"""
Enhanced canvas widget with agent configuration support.
"""

import tkinter as tk
from typing import Dict, Optional, Callable
from ..app.workflow import WorkflowGraph, WorkflowNode, WorkflowEdge
from ..core.agent import AgentConfig, VisualPosition
from .dialogs import AgentConfigDialog
from .styles import *


class EnhancedCanvasWidget(tk.Canvas):
    """Enhanced canvas with agent configuration support."""

    def __init__(self, parent, workflow: WorkflowGraph):
        """
        Initialize enhanced canvas.

        Args:
            parent: Parent widget
            workflow: WorkflowGraph to visualize
        """
        super().__init__(parent, bg=CANVAS_BG, highlightthickness=0)

        self.workflow = workflow

        # Visual state
        self.selected_node_id: Optional[str] = None
        self.dragging_node_id: Optional[str] = None
        self.drag_offset_x = 0
        self.drag_offset_y = 0

        # Link creation state
        self.creating_link = False
        self.link_source_id: Optional[str] = None
        self.temp_line = None

        # Callbacks
        self.on_node_changed: Optional[Callable] = None
        self.on_graph_changed: Optional[Callable] = None

        # Bind events
        self.bind("<ButtonPress-1>", self._on_mouse_press)
        self.bind("<B1-Motion>", self._on_mouse_drag)
        self.bind("<ButtonRelease-1>", self._on_mouse_release)
        self.bind("<Double-Button-1>", self._on_double_click)
        self.bind("<Button-3>", self._on_right_click)  # Right-click for context menu

        # Initial draw
        self.draw_graph()

    def add_agent_from_type(self, agent_type: dict, x: int, y: int):
        """
        Add a new agent from a dragged agent type.

        Args:
            agent_type: Agent type data with provider, model, system_prompt, etc.
            x: X position on canvas
            y: Y position on canvas
        """
        import uuid

        # Create unique ID
        node_id = f"agent_{uuid.uuid4().hex[:8]}"

        # Create config from agent type
        config = AgentConfig(
            id=node_id,
            name=agent_type.get("name", f"Agent {len(self.workflow.nodes) + 1}"),
            provider=agent_type["provider"],
            model=agent_type["model"],
            system_prompt=agent_type.get("system_prompt", "You are a helpful assistant."),
            temperature=0.7,
            max_tokens=4096
        )

        # Create node at drop position
        node = WorkflowNode(config, VisualPosition(x - NODE_WIDTH // 2, y - NODE_HEIGHT // 2))
        self.workflow.add_node(node)

        # Redraw
        self.draw_graph()

        # Notify
        if self.on_graph_changed:
            self.on_graph_changed()

        return node_id

    def draw_graph(self):
        """Render complete workflow graph."""
        self.delete("all")

        # Draw edges first (behind nodes)
        for edge in self.workflow.edges:
            self._draw_edge(edge)

        # Draw nodes
        for node_id, node in self.workflow.nodes.items():
            self._draw_node(node_id, node)

    def _draw_edge(self, edge: WorkflowEdge):
        """Draw an edge/link with modern styling."""
        source_node = self.workflow.get_node(edge.source_id)
        target_node = self.workflow.get_node(edge.target_id)

        if not source_node or not target_node:
            return

        # Calculate arrow positions (center of nodes)
        x1 = source_node.position.x + NODE_WIDTH // 2
        y1 = source_node.position.y + NODE_HEIGHT // 2
        x2 = target_node.position.x + NODE_WIDTH // 2
        y2 = target_node.position.y + NODE_HEIGHT // 2

        # Draw shadow line for depth
        self.create_line(
            x1 + 2, y1 + 2, x2 + 2, y2 + 2,
            arrow=tk.LAST,
            fill=SHADOW_LIGHT,
            width=EDGE_WIDTH + 1,
            arrowshape=(16, 21, 7),
            tags=("edge", f"edge_{edge.source_id}_{edge.target_id}_shadow")
        )

        # Draw main arrow
        self.create_line(
            x1, y1, x2, y2,
            arrow=tk.LAST,
            fill=EDGE_COLOR,
            width=EDGE_WIDTH + 1,
            arrowshape=(16, 21, 7),
            smooth=True,
            tags=("edge", f"edge_{edge.source_id}_{edge.target_id}")
        )

    def _draw_node(self, node_id: str, node: WorkflowNode):
        """Draw a node with modern styling."""
        x, y = node.position.x, node.position.y
        config = node.agent_config

        # Determine color based on provider
        color = get_provider_color(config.provider)

        # Determine border (selection)
        is_selected = node_id == self.selected_node_id
        border_color = SELECTION_COLOR if is_selected else NODE_BORDER
        border_width = SELECTION_WIDTH if is_selected else 2

        # Draw shadow for depth (offset by 3 pixels)
        if not is_selected:
            self.create_rectangle(
                x + 3, y + 3, x + NODE_WIDTH + 3, y + NODE_HEIGHT + 3,
                fill=SHADOW_LIGHT,
                outline="",
                tags=("node", node_id, "shadow")
            )

        # Node rectangle with rounded appearance
        self.create_rectangle(
            x, y, x + NODE_WIDTH, y + NODE_HEIGHT,
            fill=color,
            outline=border_color,
            width=border_width,
            tags=("node", node_id, "node_rect")
        )

        # Selection glow effect
        if is_selected:
            self.create_rectangle(
                x - 2, y - 2, x + NODE_WIDTH + 2, y + NODE_HEIGHT + 2,
                fill="",
                outline=SELECTION_GLOW,
                width=2,
                tags=("node", node_id, "glow")
            )

        # Agent name (title)
        self.create_text(
            x + NODE_WIDTH // 2,
            y + 22,
            text=config.name,
            fill=NODE_TEXT,
            font=("Segoe UI", FONT_SIZE_TITLE, FONT_WEIGHT_BOLD),
            tags=("node", node_id, "node_text"),
            width=NODE_WIDTH - 30
        )

        # Provider info (subtitle)
        provider_text = f"{config.provider}"
        self.create_text(
            x + NODE_WIDTH // 2,
            y + 42,
            text=provider_text,
            fill=NODE_TEXT,
            font=("Segoe UI", FONT_SIZE_SUBTITLE),
            tags=("node", node_id, "node_subtitle")
        )

        # Model info (smaller text)
        model_text = config.model[:25] + "..." if len(config.model) > 25 else config.model
        self.create_text(
            x + NODE_WIDTH // 2,
            y + 58,
            text=model_text,
            fill=NODE_TEXT,
            font=("Segoe UI", FONT_SIZE_SMALL),
            tags=("node", node_id, "node_model")
        )

        # Temperature indicator with subtle background
        temp_text = f"T={config.temperature:.1f}"
        # Use a darker overlay for contrast
        self.create_rectangle(
            x + 8, y + NODE_HEIGHT - 20,
            x + 50, y + NODE_HEIGHT - 6,
            fill="#1E293B",
            outline="",
            tags=("node", node_id)
        )
        self.create_text(
            x + 29,
            y + NODE_HEIGHT - 13,
            text=temp_text,
            fill="#FFFFFF",
            font=("Segoe UI", FONT_SIZE_SMALL, "bold"),
            tags=("node", node_id),
            anchor="center"
        )

        # Config button (gear icon) - more modern styling
        btn_x = x + NODE_WIDTH - 28
        btn_y = y + 8

        # Button background
        self.create_oval(
            btn_x, btn_y,
            btn_x + CONFIG_BUTTON_SIZE,
            btn_y + CONFIG_BUTTON_SIZE,
            fill=CONFIG_BUTTON_BG,
            outline="",
            tags=("config_btn", node_id, "config_bg")
        )

        # Button icon
        self.create_text(
            btn_x + CONFIG_BUTTON_SIZE // 2,
            btn_y + CONFIG_BUTTON_SIZE // 2,
            text="⚙",
            fill=CONFIG_BUTTON_COLOR,
            font=("Segoe UI", 11),
            tags=("config_btn", node_id)
        )

    def _find_node_at(self, x: int, y: int) -> Optional[str]:
        """Find node at position."""
        for node_id, node in self.workflow.nodes.items():
            nx, ny = node.position.x, node.position.y
            if nx <= x <= nx + NODE_WIDTH and ny <= y <= ny + NODE_HEIGHT:
                return node_id
        return None

    def _is_config_button(self, x: int, y: int, node_id: str) -> bool:
        """Check if click is on config button."""
        node = self.workflow.get_node(node_id)
        if not node:
            return False

        btn_x = node.position.x + NODE_WIDTH - 28
        btn_y = node.position.y + 8

        return (btn_x <= x <= btn_x + CONFIG_BUTTON_SIZE and
                btn_y <= y <= btn_y + CONFIG_BUTTON_SIZE)

    def _on_mouse_press(self, event):
        """Handle mouse press."""
        node_id = self._find_node_at(event.x, event.y)

        if node_id:
            # Check if config button clicked
            if self._is_config_button(event.x, event.y, node_id):
                self._show_config_dialog(node_id)
                return

            # Start dragging
            self.selected_node_id = node_id
            self.dragging_node_id = node_id

            node = self.workflow.get_node(node_id)
            self.drag_offset_x = event.x - node.position.x
            self.drag_offset_y = event.y - node.position.y

            self.config(cursor="fleur")
            self.draw_graph()  # Redraw to show selection
        else:
            # Clicked on empty space
            self.selected_node_id = None
            self.draw_graph()

    def _on_mouse_drag(self, event):
        """Handle mouse drag."""
        if self.dragging_node_id:
            node = self.workflow.get_node(self.dragging_node_id)
            if node:
                # Update position
                node.position.x = event.x - self.drag_offset_x
                node.position.y = event.y - self.drag_offset_y

                # Redraw
                self.draw_graph()

    def _on_mouse_release(self, event):
        """Handle mouse release."""
        if self.dragging_node_id:
            self.dragging_node_id = None
            self.config(cursor="")

            # Notify change
            if self.on_graph_changed:
                self.on_graph_changed()

    def _on_double_click(self, event):
        """Handle double-click to configure node."""
        node_id = self._find_node_at(event.x, event.y)
        if node_id:
            self._show_config_dialog(node_id)

    def _on_right_click(self, event):
        """Handle right-click for context menu."""
        # Create context menu
        menu = tk.Menu(self, tearoff=0)

        node_id = self._find_node_at(event.x, event.y)

        if node_id:
            # Node context menu
            menu.add_command(
                label="Configure Agent",
                command=lambda: self._show_config_dialog(node_id)
            )
            menu.add_command(
                label="Create Link From Here",
                command=lambda: self._start_link_creation(node_id)
            )
            menu.add_separator()
            menu.add_command(
                label="Delete Agent",
                command=lambda: self._delete_node(node_id)
            )
        else:
            # Canvas context menu
            menu.add_command(
                label="Add New Agent",
                command=lambda: self._add_new_node(event.x, event.y)
            )

        menu.post(event.x_root, event.y_root)

    def _show_config_dialog(self, node_id: str):
        """Show configuration dialog for node."""
        node = self.workflow.get_node(node_id)
        if not node:
            return

        dialog = AgentConfigDialog(self, node.agent_config)
        self.wait_window(dialog)

        if dialog.result:
            # Update config
            node.agent_config = dialog.result

            # Redraw
            self.draw_graph()

            # Notify
            if self.on_node_changed:
                self.on_node_changed(node_id, dialog.result)

    def _start_link_creation(self, source_id: str):
        """Start creating a link from a node."""
        self.creating_link = True
        self.link_source_id = source_id
        print(f"Link creation started from {source_id}. Click target node to complete.")

        # Highlight source
        self.selected_node_id = source_id
        self.draw_graph()

    def _add_new_node(self, x: int, y: int):
        """Add a new agent node."""
        import uuid

        # Create default config
        node_id = f"agent_{uuid.uuid4().hex[:8]}"

        config = AgentConfig(
            id=node_id,
            name=f"Agent {len(self.workflow.nodes) + 1}",
            provider="anthropic",
            model="claude-sonnet-4-5-20250929",
            system_prompt="You are a helpful assistant.",
            temperature=0.7,
            max_tokens=4096
        )

        # Create node
        node = WorkflowNode(config, VisualPosition(x, y))
        self.workflow.add_node(node)

        # Redraw
        self.draw_graph()

        # Notify
        if self.on_graph_changed:
            self.on_graph_changed()

        # Open config dialog
        self._show_config_dialog(node_id)

    def _delete_node(self, node_id: str):
        """Delete a node."""
        import tkinter.messagebox as messagebox

        node = self.workflow.get_node(node_id)
        if not node:
            return

        # Confirm
        result = messagebox.askyesno(
            "Delete Agent",
            f"Delete agent '{node.agent_config.name}'?\nAll connected links will also be removed."
        )

        if result:
            self.workflow.remove_node(node_id)
            self.selected_node_id = None

            # Redraw
            self.draw_graph()

            # Notify
            if self.on_graph_changed:
                self.on_graph_changed()

    def add_link(self, source_id: str, target_id: str):
        """
        Add a link between two nodes.

        Args:
            source_id: Source node ID
            target_id: Target node ID
        """
        try:
            edge = WorkflowEdge(source_id, target_id)
            self.workflow.add_edge(edge)

            # Redraw
            self.draw_graph()

            # Notify
            if self.on_graph_changed:
                self.on_graph_changed()

            print(f"Link created: {source_id} -> {target_id}")

        except ValueError as e:
            import tkinter.messagebox as messagebox
            messagebox.showerror("Error", str(e))
