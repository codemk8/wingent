"""
Configuration dialogs for agents.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
from typing import Optional
from ..core.agent import AgentConfig


class AgentConfigDialog(tk.Toplevel):
    """Dialog for configuring agent properties."""

    # Model lists for each provider
    MODELS = {
        "anthropic": [
            "claude-opus-4-5-20251101",
            "claude-sonnet-4-5-20250929",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307"
        ],
        "openai": [
            "gpt-4-turbo",
            "gpt-4-turbo-2024-04-09",
            "gpt-4",
            "gpt-4-0613",
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-0125"
        ],
        "local": [
            "llama3",
            "llama3:70b",
            "llama3:8b",
            "mistral",
            "mistral:7b",
            "codellama",
            "codellama:13b",
            "phi3",
            "gemma:7b"
        ]
    }

    def __init__(self, parent, config: AgentConfig):
        """
        Initialize agent configuration dialog.

        Args:
            parent: Parent widget
            config: AgentConfig to edit
        """
        super().__init__(parent)
        self.title(f"Configure Agent: {config.name}")
        self.geometry("600x700")
        self.resizable(False, False)

        self.config = config
        self.result: Optional[AgentConfig] = None

        self._create_widgets()

        # Make dialog modal
        self.transient(parent)

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _create_widgets(self):
        """Create dialog widgets."""
        # Main container with padding
        main_frame = tk.Frame(self, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Name
        name_frame = tk.Frame(main_frame)
        name_frame.pack(fill=tk.X, pady=(0, 10))
        tk.Label(name_frame, text="Agent Name:", font=("Arial", 10, "bold")).pack(anchor="w")
        self.name_entry = tk.Entry(name_frame, width=50, font=("Arial", 10))
        self.name_entry.insert(0, self.config.name)
        self.name_entry.pack(fill=tk.X, pady=(5, 0))

        # Provider selection
        provider_frame = tk.Frame(main_frame)
        provider_frame.pack(fill=tk.X, pady=(0, 10))
        tk.Label(provider_frame, text="LLM Provider:", font=("Arial", 10, "bold")).pack(anchor="w")

        provider_buttons_frame = tk.Frame(provider_frame)
        provider_buttons_frame.pack(fill=tk.X, pady=(5, 0))

        self.provider_var = tk.StringVar(value=self.config.provider)

        providers = [
            ("Anthropic (Claude)", "anthropic"),
            ("OpenAI (GPT)", "openai"),
            ("Local (Ollama)", "local")
        ]

        for label, value in providers:
            rb = tk.Radiobutton(
                provider_buttons_frame,
                text=label,
                variable=self.provider_var,
                value=value,
                command=self._on_provider_changed,
                font=("Arial", 9)
            )
            rb.pack(side=tk.LEFT, padx=(0, 15))

        # Model selection
        model_frame = tk.Frame(main_frame)
        model_frame.pack(fill=tk.X, pady=(0, 10))
        tk.Label(model_frame, text="Model:", font=("Arial", 10, "bold")).pack(anchor="w")

        self.model_var = tk.StringVar(value=self.config.model)
        self.model_dropdown = ttk.Combobox(
            model_frame,
            textvariable=self.model_var,
            width=47,
            font=("Arial", 9),
            state="readonly"
        )
        self.model_dropdown.pack(fill=tk.X, pady=(5, 0))
        self._update_model_list()

        # System prompt
        prompt_frame = tk.Frame(main_frame)
        prompt_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        tk.Label(prompt_frame, text="System Prompt / Role:", font=("Arial", 10, "bold")).pack(anchor="w")

        self.prompt_text = scrolledtext.ScrolledText(
            prompt_frame,
            width=50,
            height=10,
            font=("Arial", 9),
            wrap=tk.WORD
        )
        self.prompt_text.insert("1.0", self.config.system_prompt)
        self.prompt_text.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        # Parameters frame
        params_frame = tk.LabelFrame(main_frame, text="Parameters", font=("Arial", 10, "bold"), padx=10, pady=10)
        params_frame.pack(fill=tk.X, pady=(0, 10))

        # Temperature
        temp_frame = tk.Frame(params_frame)
        temp_frame.pack(fill=tk.X, pady=(0, 10))

        temp_label_frame = tk.Frame(temp_frame)
        temp_label_frame.pack(fill=tk.X)
        tk.Label(temp_label_frame, text="Temperature:", font=("Arial", 9)).pack(side=tk.LEFT)
        self.temp_value_label = tk.Label(temp_label_frame, text=f"{self.config.temperature:.1f}", font=("Arial", 9, "bold"))
        self.temp_value_label.pack(side=tk.RIGHT)

        self.temp_scale = tk.Scale(
            temp_frame,
            from_=0.0,
            to=2.0,
            resolution=0.1,
            orient=tk.HORIZONTAL,
            showvalue=0,
            command=self._on_temp_changed
        )
        self.temp_scale.set(self.config.temperature)
        self.temp_scale.pack(fill=tk.X, pady=(5, 0))

        # Max tokens
        tokens_frame = tk.Frame(params_frame)
        tokens_frame.pack(fill=tk.X)
        tk.Label(tokens_frame, text="Max Tokens:", font=("Arial", 9)).pack(side=tk.LEFT)

        self.tokens_var = tk.StringVar(value=str(self.config.max_tokens))
        tokens_entry = tk.Entry(tokens_frame, textvariable=self.tokens_var, width=10, font=("Arial", 9))
        tokens_entry.pack(side=tk.RIGHT)

        # Buttons
        btn_frame = tk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        cancel_btn = tk.Button(
            btn_frame,
            text="Cancel",
            command=self._on_cancel,
            width=12,
            font=("Arial", 10),
            bg="#9CA3AF",
            fg="white",
            relief=tk.FLAT,
            cursor="hand2"
        )
        cancel_btn.pack(side=tk.RIGHT, padx=(5, 0))

        ok_btn = tk.Button(
            btn_frame,
            text="OK",
            command=self._on_ok,
            width=12,
            font=("Arial", 10),
            bg="#3B82F6",
            fg="white",
            relief=tk.FLAT,
            cursor="hand2"
        )
        ok_btn.pack(side=tk.RIGHT)

    def _update_model_list(self):
        """Update model dropdown based on selected provider."""
        provider = self.provider_var.get()
        models = self.MODELS.get(provider, [])
        self.model_dropdown["values"] = models

        # Set default model if current model not in list
        if self.model_var.get() not in models and models:
            self.model_var.set(models[0])

    def _on_provider_changed(self):
        """Handle provider change."""
        self._update_model_list()

    def _on_temp_changed(self, value):
        """Handle temperature slider change."""
        self.temp_value_label.config(text=f"{float(value):.1f}")

    def _on_ok(self):
        """Save configuration and close."""
        try:
            max_tokens = int(self.tokens_var.get())
            if max_tokens < 1:
                raise ValueError("Max tokens must be at least 1")
        except ValueError as e:
            tk.messagebox.showerror("Invalid Input", f"Invalid max tokens: {e}")
            return

        self.result = AgentConfig(
            id=self.config.id,
            name=self.name_entry.get().strip(),
            provider=self.provider_var.get(),
            model=self.model_var.get(),
            system_prompt=self.prompt_text.get("1.0", "end-1c"),
            temperature=self.temp_scale.get(),
            max_tokens=max_tokens,
            metadata=self.config.metadata
        )
        self.destroy()

    def _on_cancel(self):
        """Cancel and close."""
        self.result = None
        self.destroy()


class InitialMessageDialog(tk.Toplevel):
    """Dialog for entering initial message to start workflow."""

    def __init__(self, parent, agent_names: list):
        """
        Initialize dialog.

        Args:
            parent: Parent widget
            agent_names: List of available agent names
        """
        super().__init__(parent)
        self.title("Send Initial Message")
        self.geometry("500x400")
        self.resizable(False, False)

        self.result: Optional[dict] = None

        self._create_widgets(agent_names)

        # Make modal
        self.transient(parent)

        # Center
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _create_widgets(self, agent_names):
        """Create widgets."""
        main_frame = tk.Frame(self, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Recipient selection
        tk.Label(main_frame, text="Send to Agent:", font=("Arial", 10, "bold")).pack(anchor="w")

        self.recipient_var = tk.StringVar(value=agent_names[0] if agent_names else "")
        recipient_dropdown = ttk.Combobox(
            main_frame,
            textvariable=self.recipient_var,
            values=agent_names,
            state="readonly",
            font=("Arial", 9),
            width=40
        )
        recipient_dropdown.pack(fill=tk.X, pady=(5, 15))

        # Message content
        tk.Label(main_frame, text="Message:", font=("Arial", 10, "bold")).pack(anchor="w")

        self.message_text = scrolledtext.ScrolledText(
            main_frame,
            width=50,
            height=12,
            font=("Arial", 9),
            wrap=tk.WORD
        )
        self.message_text.pack(fill=tk.BOTH, expand=True, pady=(5, 15))
        self.message_text.focus()

        # Buttons
        btn_frame = tk.Frame(main_frame)
        btn_frame.pack(fill=tk.X)

        cancel_btn = tk.Button(
            btn_frame,
            text="Cancel",
            command=self._on_cancel,
            width=12,
            font=("Arial", 10),
            bg="#9CA3AF",
            fg="white",
            relief=tk.FLAT
        )
        cancel_btn.pack(side=tk.RIGHT, padx=(5, 0))

        send_btn = tk.Button(
            btn_frame,
            text="Send",
            command=self._on_send,
            width=12,
            font=("Arial", 10),
            bg="#10B981",
            fg="white",
            relief=tk.FLAT
        )
        send_btn.pack(side=tk.RIGHT)

    def _on_send(self):
        """Send message."""
        message = self.message_text.get("1.0", "end-1c").strip()
        if not message:
            tk.messagebox.showwarning("Empty Message", "Please enter a message")
            return

        self.result = {
            "recipient": self.recipient_var.get(),
            "content": message
        }
        self.destroy()

    def _on_cancel(self):
        """Cancel."""
        self.result = None
        self.destroy()
