"""
Explorer panel with topology templates and agent types palette.
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional, Dict, List
from .styles import *


class ExplorerPanel(tk.Frame):
    """Left sidebar explorer panel with tabs."""

    def __init__(self, parent, on_add_template: Optional[Callable] = None,
                 on_drag_agent_type: Optional[Callable] = None):
        """
        Initialize explorer panel.

        Args:
            parent: Parent widget
            on_add_template: Callback when template is selected (topology_data)
            on_drag_agent_type: Callback when agent type is dragged (agent_type_data, x, y)
        """
        super().__init__(parent, bg="#FFFFFF")

        self.on_add_template = on_add_template
        self.on_drag_agent_type = on_drag_agent_type

        self._create_widgets()

    def _create_widgets(self):
        """Create panel widgets."""
        # Header
        header = tk.Frame(self, bg=HEADER_BG, height=40)
        header.pack(side=tk.TOP, fill=tk.X)
        header.pack_propagate(False)

        tk.Label(
            header,
            text="Explorer",
            font=("Segoe UI", 11, "bold"),
            fg=HEADER_TEXT,
            bg=HEADER_BG
        ).pack(side=tk.LEFT, padx=15, pady=8)

        # Notebook (tabs)
        style = ttk.Style()
        style.theme_use('default')
        style.configure('TNotebook', background="#FFFFFF", borderwidth=0)
        style.configure('TNotebook.Tab', padding=[12, 8], font=('Segoe UI', 9))

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        # Tab 1: Topology Templates
        self.topology_tab = TopologyTemplatesTab(self.notebook, self.on_add_template)
        self.notebook.add(self.topology_tab, text="Templates")

        # Tab 2: Agent Types Palette
        self.palette_tab = AgentTypesPaletteTab(self.notebook, self.on_drag_agent_type)
        self.notebook.add(self.palette_tab, text="Agent Types")


class TopologyTemplatesTab(tk.Frame):
    """Tab showing popular topology templates."""

    def __init__(self, parent, on_add_template: Optional[Callable] = None):
        """
        Initialize topology templates tab.

        Args:
            parent: Parent widget
            on_add_template: Callback when template is selected
        """
        super().__init__(parent, bg="#F8FAFC")

        self.on_add_template = on_add_template

        # Popular topologies
        self.templates = [
            {
                "name": "Research Pipeline",
                "description": "Researcher → Writer → Editor",
                "icon": "📚",
                "agents": [
                    {"name": "Researcher", "provider": "anthropic", "model": "claude-sonnet-4-5-20250929",
                     "prompt": "You are a research assistant. Analyze questions and provide well-researched insights.",
                     "x": 100, "y": 150},
                    {"name": "Writer", "provider": "anthropic", "model": "claude-sonnet-4-5-20250929",
                     "prompt": "You are a writer. Take research and create clear, concise summaries.",
                     "x": 400, "y": 150},
                    {"name": "Editor", "provider": "anthropic", "model": "claude-3-5-haiku-20241022",
                     "prompt": "You are an editor. Review and refine written content for clarity and impact.",
                     "x": 700, "y": 150}
                ],
                "edges": [("agent_0", "agent_1"), ("agent_1", "agent_2")]
            },
            {
                "name": "Debate System",
                "description": "Two agents debate, moderator decides",
                "icon": "⚖️",
                "agents": [
                    {"name": "Advocate", "provider": "anthropic", "model": "claude-sonnet-4-5-20250929",
                     "prompt": "You are an advocate. Argue in favor of ideas and find supporting evidence.",
                     "x": 150, "y": 100},
                    {"name": "Critic", "provider": "anthropic", "model": "claude-sonnet-4-5-20250929",
                     "prompt": "You are a critic. Challenge ideas and identify potential flaws.",
                     "x": 150, "y": 300},
                    {"name": "Moderator", "provider": "anthropic", "model": "claude-sonnet-4-5-20250929",
                     "prompt": "You are a moderator. Synthesize different viewpoints and reach balanced conclusions.",
                     "x": 500, "y": 200}
                ],
                "edges": [("agent_0", "agent_2"), ("agent_1", "agent_2")]
            },
            {
                "name": "Parallel Analysis",
                "description": "Multiple agents analyze in parallel",
                "icon": "🔀",
                "agents": [
                    {"name": "Analyst A", "provider": "anthropic", "model": "claude-sonnet-4-5-20250929",
                     "prompt": "You are a data analyst focusing on quantitative analysis.",
                     "x": 200, "y": 100},
                    {"name": "Analyst B", "provider": "anthropic", "model": "claude-sonnet-4-5-20250929",
                     "prompt": "You are a data analyst focusing on qualitative insights.",
                     "x": 200, "y": 250},
                    {"name": "Synthesizer", "provider": "anthropic", "model": "claude-sonnet-4-5-20250929",
                     "prompt": "You synthesize multiple analyses into coherent conclusions.",
                     "x": 550, "y": 175}
                ],
                "edges": [("agent_0", "agent_2"), ("agent_1", "agent_2")]
            },
            {
                "name": "Review Chain",
                "description": "Sequential review and refinement",
                "icon": "🔄",
                "agents": [
                    {"name": "Drafter", "provider": "anthropic", "model": "claude-3-5-haiku-20241022",
                     "prompt": "You create initial drafts quickly based on requirements.",
                     "x": 150, "y": 200},
                    {"name": "Reviewer", "provider": "anthropic", "model": "claude-sonnet-4-5-20250929",
                     "prompt": "You review drafts for quality, accuracy, and completeness.",
                     "x": 450, "y": 200},
                    {"name": "Finalizer", "provider": "anthropic", "model": "claude-sonnet-4-5-20250929",
                     "prompt": "You polish reviewed content and ensure it meets all requirements.",
                     "x": 750, "y": 200}
                ],
                "edges": [("agent_0", "agent_1"), ("agent_1", "agent_2")]
            }
        ]

        self._create_widgets()

    def _create_widgets(self):
        """Create template list."""
        # Scrollable container
        canvas = tk.Canvas(self, bg="#F8FAFC", highlightthickness=0)
        scrollbar = tk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#F8FAFC")

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Add templates
        for template in self.templates:
            self._create_template_item(scrollable_frame, template)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _create_template_item(self, parent, template: Dict):
        """Create a template item widget."""
        # Container
        container = tk.Frame(parent, bg="#FFFFFF", relief=tk.FLAT, borderwidth=1)
        container.pack(fill=tk.X, padx=SPACING_SM, pady=SPACING_SM)

        # Inner frame with padding
        inner = tk.Frame(container, bg="#FFFFFF")
        inner.pack(fill=tk.BOTH, expand=True, padx=SPACING_MD, pady=SPACING_MD)

        # Icon and title row
        header = tk.Frame(inner, bg="#FFFFFF")
        header.pack(fill=tk.X)

        tk.Label(
            header,
            text=template["icon"],
            font=("Segoe UI", 16),
            bg="#FFFFFF"
        ).pack(side=tk.LEFT, padx=(0, SPACING_SM))

        tk.Label(
            header,
            text=template["name"],
            font=("Segoe UI", 10, "bold"),
            bg="#FFFFFF",
            fg="#1E293B"
        ).pack(side=tk.LEFT)

        # Description
        tk.Label(
            inner,
            text=template["description"],
            font=("Segoe UI", 8),
            bg="#FFFFFF",
            fg="#64748B",
            wraplength=220,
            justify=tk.LEFT
        ).pack(fill=tk.X, pady=(SPACING_XS, SPACING_SM))

        # Use button
        btn = tk.Button(
            inner,
            text="Use Template",
            font=("Segoe UI", 8),
            bg=BUTTON_PRIMARY,
            fg="#FFFFFF",
            relief=tk.FLAT,
            cursor="hand2",
            command=lambda t=template: self._on_template_click(t)
        )
        btn.pack(fill=tk.X)

        # Hover effects
        def on_enter(e):
            btn.config(bg=BUTTON_PRIMARY_HOVER)

        def on_leave(e):
            btn.config(bg=BUTTON_PRIMARY)

        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)

    def _on_template_click(self, template: Dict):
        """Handle template click."""
        if self.on_add_template:
            self.on_add_template(template)


class AgentTypesPaletteTab(tk.Frame):
    """Tab showing draggable agent types."""

    def __init__(self, parent, on_drag_agent_type: Optional[Callable] = None):
        """
        Initialize agent types palette tab.

        Args:
            parent: Parent widget
            on_drag_agent_type: Callback for drag operations
        """
        super().__init__(parent, bg="#F8FAFC")

        self.on_drag_agent_type = on_drag_agent_type

        # Agent type definitions (agent roles)
        self.agent_types = [
            {
                "name": "Researcher",
                "provider": "anthropic",
                "model": "claude-sonnet-4-5-20250929",
                "icon": "🔍",
                "color": "#3B82F6",  # Blue
                "description": "Analyzes questions and provides well-researched insights",
                "system_prompt": "You are a research assistant. Analyze questions and provide well-researched insights with supporting evidence."
            },
            {
                "name": "Writer",
                "provider": "anthropic",
                "model": "claude-sonnet-4-5-20250929",
                "icon": "✍️",
                "color": "#10B981",  # Green
                "description": "Creates clear, engaging written content",
                "system_prompt": "You are a professional writer. Take information and create clear, engaging, and well-structured written content."
            },
            {
                "name": "Editor",
                "provider": "anthropic",
                "model": "claude-3-5-haiku-20241022",
                "icon": "📝",
                "color": "#F59E0B",  # Amber
                "description": "Reviews and refines content for clarity",
                "system_prompt": "You are an editor. Review and refine written content for clarity, coherence, and impact."
            },
            {
                "name": "Analyst",
                "provider": "anthropic",
                "model": "claude-sonnet-4-5-20250929",
                "icon": "📊",
                "color": "#8B5CF6",  # Purple
                "description": "Analyzes data and identifies patterns",
                "system_prompt": "You are a data analyst. Analyze information, identify patterns, and provide actionable insights."
            },
            {
                "name": "Critic",
                "provider": "anthropic",
                "model": "claude-sonnet-4-5-20250929",
                "icon": "🔎",
                "color": "#EF4444",  # Red
                "description": "Identifies flaws and challenges ideas",
                "system_prompt": "You are a critic. Challenge ideas, identify potential flaws, and provide constructive criticism."
            },
            {
                "name": "Moderator",
                "provider": "anthropic",
                "model": "claude-sonnet-4-5-20250929",
                "icon": "⚖️",
                "color": "#6366F1",  # Indigo
                "description": "Synthesizes viewpoints and reaches conclusions",
                "system_prompt": "You are a moderator. Synthesize different viewpoints and reach balanced, well-reasoned conclusions."
            },
            {
                "name": "Code Reviewer",
                "provider": "anthropic",
                "model": "claude-sonnet-4-5-20250929",
                "icon": "💻",
                "color": "#EC4899",  # Pink
                "description": "Reviews code for quality and best practices",
                "system_prompt": "You are a code reviewer. Review code for quality, best practices, potential bugs, and suggest improvements."
            },
            {
                "name": "Summarizer",
                "provider": "anthropic",
                "model": "claude-3-5-haiku-20241022",
                "icon": "📋",
                "color": "#14B8A6",  # Teal
                "description": "Creates concise summaries of information",
                "system_prompt": "You are a summarizer. Create concise, accurate summaries that capture the key points of information."
            },
            {
                "name": "Planner",
                "provider": "anthropic",
                "model": "claude-sonnet-4-5-20250929",
                "icon": "🗓️",
                "color": "#F97316",  # Orange
                "description": "Creates structured plans and strategies",
                "system_prompt": "You are a planner. Create structured plans, break down tasks, and develop strategies to achieve goals."
            },
            {
                "name": "Translator",
                "provider": "anthropic",
                "model": "claude-sonnet-4-5-20250929",
                "icon": "🌐",
                "color": "#06B6D4",  # Cyan
                "description": "Translates and adapts content",
                "system_prompt": "You are a translator. Translate content accurately while preserving meaning, tone, and cultural context."
            }
        ]

        self._create_widgets()

    def _create_widgets(self):
        """Create palette items."""
        # Instructions
        info = tk.Frame(self, bg="#E0E7FF")
        info.pack(fill=tk.X, padx=SPACING_SM, pady=SPACING_SM)

        tk.Label(
            info,
            text="💡 Drag agent types to the canvas",
            font=("Segoe UI", 8),
            bg="#E0E7FF",
            fg="#3730A3",
            anchor=tk.W
        ).pack(fill=tk.X, padx=SPACING_MD, pady=SPACING_SM)

        # Scrollable container
        canvas = tk.Canvas(self, bg="#F8FAFC", highlightthickness=0)
        scrollbar = tk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#F8FAFC")

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Add agent types
        for agent_type in self.agent_types:
            self._create_agent_type_item(scrollable_frame, agent_type)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _create_agent_type_item(self, parent, agent_type: Dict):
        """Create a draggable agent type item."""
        # Container
        container = tk.Frame(parent, bg=agent_type["color"], relief=tk.RAISED, borderwidth=2, cursor="hand2")
        container.pack(fill=tk.X, padx=SPACING_SM, pady=SPACING_SM)

        # Store agent type data
        container.agent_type = agent_type

        # Inner frame
        inner = tk.Frame(container, bg=agent_type["color"])
        inner.pack(fill=tk.BOTH, expand=True, padx=SPACING_MD, pady=SPACING_MD)

        # Icon and name
        header = tk.Frame(inner, bg=agent_type["color"])
        header.pack(fill=tk.X)

        tk.Label(
            header,
            text=agent_type["icon"],
            font=("Segoe UI", 14),
            bg=agent_type["color"]
        ).pack(side=tk.LEFT, padx=(0, SPACING_SM))

        tk.Label(
            header,
            text=agent_type["name"],
            font=("Segoe UI", 9, "bold"),
            bg=agent_type["color"],
            fg="#FFFFFF"
        ).pack(side=tk.LEFT)

        # Description
        tk.Label(
            inner,
            text=agent_type["description"],
            font=("Segoe UI", 7),
            bg=agent_type["color"],
            fg="#FFFFFF",
            wraplength=200,
            justify=tk.LEFT
        ).pack(fill=tk.X, pady=(SPACING_XS, 0))

        # Bind drag events
        container.bind("<ButtonPress-1>", lambda e, at=agent_type: self._on_drag_start(e, at))
        container.bind("<B1-Motion>", self._on_drag_motion)
        container.bind("<ButtonRelease-1>", self._on_drag_end)

        # Hover effect
        def on_enter(e):
            container.config(relief=tk.GROOVE)

        def on_leave(e):
            container.config(relief=tk.RAISED)

        container.bind("<Enter>", on_enter)
        container.bind("<Leave>", on_leave)

    def _on_drag_start(self, event, agent_type: Dict):
        """Handle drag start."""
        self.drag_data = {
            "agent_type": agent_type,
            "start_x": event.x_root,
            "start_y": event.y_root
        }

    def _on_drag_motion(self, event):
        """Handle drag motion."""
        # Could show visual feedback here
        pass

    def _on_drag_end(self, event):
        """Handle drag end."""
        if hasattr(self, 'drag_data') and self.on_drag_agent_type:
            # Calculate drop position relative to canvas
            # The callback will handle the actual placement
            self.on_drag_agent_type(
                self.drag_data["agent_type"],
                event.x_root,
                event.y_root
            )

        if hasattr(self, 'drag_data'):
            del self.drag_data
