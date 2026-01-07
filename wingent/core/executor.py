"""
Execution engine for running workflows.
"""

import asyncio
from typing import Dict, List, Optional, Callable
from ..app.workflow import WorkflowGraph
from .agent import Agent
from .message import Message, MessageChannel


class ExecutionEngine:
    """Manages workflow execution."""

    def __init__(self, workflow: WorkflowGraph, provider_factory: Optional[Callable] = None):
        """
        Initialize execution engine.

        Args:
            workflow: WorkflowGraph to execute
            provider_factory: Optional factory function to create providers
                             Signature: (provider_name: str, model: str) -> LLMProvider
        """
        self.workflow = workflow
        self.provider_factory = provider_factory
        self.agents: Dict[str, Agent] = {}
        self.channels: Dict[tuple, MessageChannel] = {}
        self.agent_inboxes: Dict[str, asyncio.Queue] = {}  # Direct inbox for each agent
        self.running = False
        self._tasks: List[asyncio.Task] = []
        self._message_log: List[Message] = []
        self._message_callbacks: List[Callable[[Message], None]] = []

    async def initialize(self):
        """Initialize agents and channels from workflow."""
        print(f"Initializing execution engine with {len(self.workflow.nodes)} agents...")

        # Create agent instances
        for node_id, node in self.workflow.nodes.items():
            config = node.agent_config

            # Create provider
            if self.provider_factory:
                provider = self.provider_factory(config.provider, config.model)
            else:
                provider = self._default_provider_factory(config.provider, config.model)

            # Create agent
            self.agents[node_id] = Agent(config, provider)

            # Create inbox for direct messages
            self.agent_inboxes[node_id] = asyncio.Queue()

            print(f"  Created agent: {config.name} ({config.id})")

        # Create message channels
        for edge in self.workflow.edges:
            channel_key = (edge.source_id, edge.target_id)
            self.channels[channel_key] = MessageChannel(
                edge.source_id,
                edge.target_id
            )
            print(f"  Created channel: {edge.source_id} -> {edge.target_id}")

        print(f"Initialization complete: {len(self.agents)} agents, {len(self.channels)} channels")

    def _default_provider_factory(self, provider_name: str, model: str):
        """
        Default provider factory.

        Args:
            provider_name: Provider name ("anthropic", "openai", "local")
            model: Model name

        Returns:
            Provider instance
        """
        if provider_name == "anthropic":
            from ..providers.anthropic import AnthropicProvider
            return AnthropicProvider()
        elif provider_name == "openai":
            from ..providers.openai import OpenAIProvider
            return OpenAIProvider()
        elif provider_name == "local":
            from ..providers.local import LocalProvider
            return LocalProvider()
        else:
            raise ValueError(f"Unknown provider: {provider_name}")

    async def start(self, initial_messages: Optional[List[Message]] = None):
        """
        Start workflow execution.

        Args:
            initial_messages: Optional list of initial messages to seed the workflow
        """
        if self.running:
            raise RuntimeError("Execution engine is already running")

        print("\n=== Starting workflow execution ===")
        self.running = True

        # Send initial messages if provided
        if initial_messages:
            print(f"Sending {len(initial_messages)} initial messages...")
            for message in initial_messages:
                await self._route_message(message)
                self._log_message(message)

        # Start agent processing loops
        print(f"Starting {len(self.agents)} agent loops...")
        self._tasks = [
            asyncio.create_task(self._agent_loop(agent_id, agent))
            for agent_id, agent in self.agents.items()
        ]

        # Wait for all tasks (or until stopped)
        try:
            await asyncio.gather(*self._tasks)
        except asyncio.CancelledError:
            print("Execution cancelled")

    async def _agent_loop(self, agent_id: str, agent: Agent):
        """
        Main processing loop for an agent.

        Args:
            agent_id: Agent ID
            agent: Agent instance
        """
        print(f"[{agent.config.name}] Agent loop started")

        while self.running:
            message_received = False
            message = None

            # First check inbox for direct messages
            inbox = self.agent_inboxes[agent_id]
            try:
                message = inbox.get_nowait()
                message_received = True
                print(f"[{agent.config.name}] Received message from inbox (sender: {message.sender_id})")
            except asyncio.QueueEmpty:
                pass

            # If no inbox message, check incoming channels
            if not message_received:
                incoming_channels = [
                    channel for (src, tgt), channel in self.channels.items()
                    if tgt == agent_id
                ]

                for channel in incoming_channels:
                    try:
                        # Try to receive message with short timeout
                        message = await channel.receive(timeout=0.1)

                        if message:
                            message_received = True
                            print(f"[{agent.config.name}] Received message from {message.sender_id}")
                            break

                    except Exception as e:
                        # Channel error or timeout
                        if not isinstance(e, asyncio.TimeoutError):
                            print(f"[{agent.config.name}] Channel error: {e}")

            # Process message if received
            if message_received and message:
                try:
                    response = await agent.process_message(message)
                    print(f"[{agent.config.name}] Generated response")

                    # Log response
                    self._log_message(response)

                    # Route response to ALL outgoing channels for this agent
                    outgoing_channels = [
                        (channel, tgt) for (src, tgt), channel in self.channels.items()
                        if src == agent_id
                    ]

                    if outgoing_channels:
                        for channel, target_id in outgoing_channels:
                            # Create message for this specific target
                            outgoing_msg = Message(
                                id=str(__import__('uuid').uuid4()),
                                sender_id=agent_id,
                                recipient_id=target_id,
                                content=response.content,
                                timestamp=response.timestamp,
                                metadata=response.metadata,
                                parent_id=response.id
                            )
                            await self._route_message(outgoing_msg)
                    else:
                        # No outgoing channels, just log the response
                        print(f"[{agent.config.name}] No outgoing channels, response not forwarded")

                except Exception as e:
                    print(f"[{agent.config.name}] Error processing message: {e}")
                    import traceback
                    traceback.print_exc()

            # If no messages received, wait a bit before checking again
            if not message_received:
                await asyncio.sleep(0.1)

        print(f"[{agent.config.name}] Agent loop stopped")

    async def _route_message(self, message: Message):
        """
        Route message to appropriate channel(s).

        Args:
            message: Message to route
        """
        routed = False

        # Find channels that match this message's sender and recipient
        for (src, tgt), channel in self.channels.items():
            if src == message.sender_id and tgt == message.recipient_id:
                try:
                    await channel.send(message)
                    print(f"  Routed message: {message.sender_id} -> {message.recipient_id}")
                    routed = True
                except Exception as e:
                    print(f"  Failed to route message: {e}")

        # If no channel found, try to deliver to agent inbox (for initial/external messages)
        if not routed and message.recipient_id in self.agent_inboxes:
            try:
                await self.agent_inboxes[message.recipient_id].put(message)
                print(f"  Routed message to inbox: {message.sender_id} -> {message.recipient_id}")
                routed = True
            except Exception as e:
                print(f"  Failed to route to inbox: {e}")

        if not routed:
            print(f"  Warning: Could not route message {message.sender_id} -> {message.recipient_id}")

    def _log_message(self, message: Message):
        """
        Log message and notify callbacks.

        Args:
            message: Message to log
        """
        self._message_log.append(message)

        # Notify callbacks
        for callback in self._message_callbacks:
            try:
                callback(message)
            except Exception as e:
                print(f"Error in message callback: {e}")

    def add_message_callback(self, callback: Callable[[Message], None]):
        """
        Add callback to be called when messages are sent.

        Args:
            callback: Callback function taking Message parameter
        """
        self._message_callbacks.append(callback)

    def get_message_log(self) -> List[Message]:
        """
        Get all logged messages.

        Returns:
            List of messages
        """
        return self._message_log.copy()

    async def stop(self):
        """Stop workflow execution."""
        print("\n=== Stopping workflow execution ===")
        self.running = False

        # Cancel all tasks
        for task in self._tasks:
            task.cancel()

        # Wait for tasks to finish
        await asyncio.gather(*self._tasks, return_exceptions=True)

        # Close all channels
        for channel in self.channels.values():
            channel.close()

        print("Execution stopped")

    def get_statistics(self) -> Dict[str, any]:
        """
        Get execution statistics.

        Returns:
            Dictionary with statistics
        """
        total_tokens = 0
        total_messages = len(self._message_log)

        for message in self._message_log:
            usage = message.metadata.get("usage", {})
            total_tokens += usage.get("total_tokens", 0)

        return {
            "total_messages": total_messages,
            "total_tokens": total_tokens,
            "agents": len(self.agents),
            "channels": len(self.channels)
        }

    def __repr__(self) -> str:
        """String representation."""
        status = "running" if self.running else "stopped"
        return f"ExecutionEngine(agents={len(self.agents)}, channels={len(self.channels)}, status={status})"
