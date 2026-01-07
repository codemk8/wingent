"""
Execution monitoring panel.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
from typing import Optional, Callable
import datetime
from ..core.message import Message
from .styles import *


class ExecutionMonitor(tk.Frame):
    """Panel for monitoring workflow execution."""

    def __init__(self, parent, on_start: Optional[Callable] = None, on_stop: Optional[Callable] = None):
        """
        Initialize execution monitor.

        Args:
            parent: Parent widget
            on_start: Callback for start button
            on_stop: Callback for stop button
        """
        super().__init__(parent, bg=MONITOR_BG)

        self.on_start = on_start
        self.on_stop = on_stop

        self._message_count = 0
        self._total_tokens = 0
        self._is_running = False

        self._create_widgets()

    def _create_widgets(self):
        """Create monitor widgets."""
        # Title bar
        title_frame = tk.Frame(self, bg=HEADER_BG, height=40)
        title_frame.pack(side=tk.TOP, fill=tk.X)
        title_frame.pack_propagate(False)

        tk.Label(
            title_frame,
            text="Execution Monitor",
            font=("Segoe UI", 11, "bold"),
            fg=HEADER_TEXT,
            bg=HEADER_BG
        ).pack(side=tk.LEFT, padx=15, pady=8)

        # Control buttons (top right)
        control_frame = tk.Frame(title_frame, bg=HEADER_BG)
        control_frame.pack(side=tk.RIGHT, padx=10)

        self.start_btn = tk.Button(
            control_frame,
            text="▶ Start",
            command=self._on_start_clicked,
            bg=BUTTON_START,
            fg="white",
            font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT,
            padx=15,
            pady=6,
            cursor="hand2",
            borderwidth=0,
            activebackground=BUTTON_START_HOVER,
            activeforeground="white"
        )
        self.start_btn.pack(side=tk.LEFT, padx=2)
        self._add_button_hover(self.start_btn, BUTTON_START, BUTTON_START_HOVER)

        self.stop_btn = tk.Button(
            control_frame,
            text="⬛ Stop",
            command=self._on_stop_clicked,
            bg=BUTTON_STOP,
            fg="white",
            font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT,
            padx=15,
            pady=6,
            state=tk.DISABLED,
            cursor="hand2",
            borderwidth=0,
            activebackground=BUTTON_STOP_HOVER,
            activeforeground="white"
        )
        self.stop_btn.pack(side=tk.LEFT, padx=2)
        self._add_button_hover(self.stop_btn, BUTTON_STOP, BUTTON_STOP_HOVER)

        clear_btn = tk.Button(
            control_frame,
            text="Clear",
            command=self._on_clear,
            bg=BUTTON_CLEAR,
            fg="white",
            font=("Segoe UI", 9),
            relief=tk.FLAT,
            padx=12,
            pady=6,
            cursor="hand2",
            borderwidth=0,
            activebackground=BUTTON_CLEAR_HOVER,
            activeforeground="white"
        )
        clear_btn.pack(side=tk.LEFT, padx=2)
        self._add_button_hover(clear_btn, BUTTON_CLEAR, BUTTON_CLEAR_HOVER)

        # Message log section
        log_frame = tk.Frame(self, bg=MONITOR_BG)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Log header
        log_header = tk.Frame(log_frame, bg=MONITOR_BG)
        log_header.pack(fill=tk.X, pady=(0, 5))

        tk.Label(
            log_header,
            text="Message Log",
            font=("Arial", 10, "bold"),
            bg=MONITOR_BG,
            fg="#374151"
        ).pack(side=tk.LEFT)

        # Scrolled text for messages with shadow frame
        log_container = tk.Frame(log_frame, bg=SHADOW_MEDIUM, padx=1, pady=1)
        log_container.pack(fill=tk.BOTH, expand=True)

        self.log_text = scrolledtext.ScrolledText(
            log_container,
            width=50,
            height=15,
            font=("Consolas, Courier New", 9),
            bg=MONITOR_LOG_BG,
            fg="#1E293B",
            relief=tk.FLAT,
            borderwidth=0,
            wrap=tk.WORD,
            state=tk.DISABLED,
            padx=10,
            pady=10
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # Configure tags for message coloring
        self.log_text.tag_config("timestamp", foreground="#64748B", font=("Consolas", 8))
        self.log_text.tag_config("sender", foreground="#2563EB", font=("Consolas", 9, "bold"))
        self.log_text.tag_config("recipient", foreground="#7C3AED", font=("Consolas", 9, "bold"))
        self.log_text.tag_config("content", foreground="#1E293B")
        self.log_text.tag_config("separator", foreground="#CBD5E1")

        # Statistics bar with border
        stats_outer = tk.Frame(self, bg=SHADOW_LIGHT, padx=1, pady=1)
        stats_outer.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 10))

        stats_frame = tk.Frame(stats_outer, bg="#F8FAFC", height=38)
        stats_frame.pack(fill=tk.BOTH)
        stats_frame.pack_propagate(False)

        self.stats_label = tk.Label(
            stats_frame,
            text="Messages: 0 | Tokens: 0 | Status: Idle",
            font=("Segoe UI", 9),
            bg="#F8FAFC",
            fg="#475569",
            anchor="w"
        )
        self.stats_label.pack(fill=tk.BOTH, padx=12, pady=8)

    def add_message(self, message: Message):
        """
        Add message to execution log.

        Args:
            message: Message to log
        """
        self._message_count += 1

        # Update token count
        usage = message.metadata.get("usage", {})
        self._total_tokens += usage.get("total_tokens", 0)

        # Format timestamp
        time_str = datetime.datetime.fromtimestamp(message.timestamp).strftime("%H:%M:%S")

        # Truncate content for display
        content = message.content
        if len(content) > 200:
            content = content[:200] + "..."

        # Add to log
        self.log_text.config(state=tk.NORMAL)

        self.log_text.insert(tk.END, f"[{time_str}] ", "timestamp")
        self.log_text.insert(tk.END, f"{message.sender_id}", "sender")
        self.log_text.insert(tk.END, " → ", "separator")
        self.log_text.insert(tk.END, f"{message.recipient_id}", "recipient")
        self.log_text.insert(tk.END, "\n")
        self.log_text.insert(tk.END, f"{content}", "content")
        self.log_text.insert(tk.END, "\n")
        self.log_text.insert(tk.END, "─" * 80 + "\n", "separator")

        self.log_text.config(state=tk.DISABLED)

        # Auto-scroll to bottom
        self.log_text.see(tk.END)

        # Update statistics
        self._update_stats()

    def set_running(self, is_running: bool):
        """
        Set execution status.

        Args:
            is_running: True if execution is running
        """
        self._is_running = is_running

        if is_running:
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
        else:
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)

        self._update_stats()

    def _update_stats(self):
        """Update statistics display."""
        status = "Running" if self._is_running else "Idle"
        status_color = STATUS_RUNNING if self._is_running else STATUS_IDLE

        # Estimate cost (rough approximation)
        estimated_cost = self._total_tokens * 0.00001  # $0.01 per 1K tokens average

        self.stats_label.config(
            text=f"Messages: {self._message_count} | Tokens: {self._total_tokens:,} | "
                 f"Cost: ${estimated_cost:.4f} | Status: {status}"
        )

    def _on_start_clicked(self):
        """Handle start button click."""
        if self.on_start:
            self.on_start()

    def _on_stop_clicked(self):
        """Handle stop button click."""
        if self.on_stop:
            self.on_stop()

    def _on_clear(self):
        """Clear the message log."""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state=tk.DISABLED)

        self._message_count = 0
        self._total_tokens = 0
        self._update_stats()

    def reset(self):
        """Reset monitor to initial state."""
        self._on_clear()
        self.set_running(False)

    def _add_button_hover(self, button, normal_color, hover_color):
        """
        Add hover effect to button.

        Args:
            button: Button widget
            normal_color: Normal background color
            hover_color: Hover background color
        """
        def on_enter(e):
            if button['state'] != tk.DISABLED:
                button['background'] = hover_color

        def on_leave(e):
            if button['state'] != tk.DISABLED:
                button['background'] = normal_color

        button.bind("<Enter>", on_enter)
        button.bind("<Leave>", on_leave)
