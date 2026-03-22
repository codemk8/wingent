#!/usr/bin/env python3
"""
Test script for Phase 2: Execution Engine.
"""

import asyncio
import time
import uuid
from typing import List, Dict, Any

from wingent.core.agent import AgentConfig, VisualPosition
from wingent.core.message import Message
from wingent.app.workflow import WorkflowGraph, WorkflowNode, WorkflowEdge
from wingent.core.executor import ExecutionEngine
from wingent.providers.base import LLMProvider


class MockProvider(LLMProvider):
    """Mock LLM provider for testing."""

    def __init__(self, name: str = "mock"):
        self.name = name
        self.call_count = 0

    async def generate(
        self,
        messages: List[Dict[str, str]],
        system: str,
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate mock response."""
        self.call_count += 1

        # Simulate some processing time
        await asyncio.sleep(0.1)

        # Create a simple response based on the last message
        last_message = messages[-1]["content"] if messages else "Hello"
        response_content = f"[{self.name}] Mock response to: {last_message}"

        return {
            "content": response_content,
            "usage": {
                "input_tokens": 10,
                "output_tokens": 20,
                "total_tokens": 30
            },
            "model": kwargs.get("model", "mock-model"),
            "stop_reason": "stop"
        }

    def get_available_models(self) -> List[str]:
        """Get available models."""
        return ["mock-model"]

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate config."""
        return True


def create_test_workflow() -> WorkflowGraph:
    """Create a simple 2-agent workflow for testing."""
    workflow = WorkflowGraph()
    workflow.metadata = {"name": "Test Workflow", "version": "1.0"}

    # Create Agent 1: Researcher
    agent1 = AgentConfig(
        id="researcher",
        name="Researcher",
        provider="mock",
        model="mock-model",
        system_prompt="You are a research assistant. Analyze the input and provide insights.",
        temperature=0.7,
        max_tokens=500
    )
    node1 = WorkflowNode(agent1, VisualPosition(100, 100))
    workflow.add_node(node1)

    # Create Agent 2: Writer
    agent2 = AgentConfig(
        id="writer",
        name="Writer",
        provider="mock",
        model="mock-model",
        system_prompt="You are a writer. Take research and create a summary.",
        temperature=0.8,
        max_tokens=500
    )
    node2 = WorkflowNode(agent2, VisualPosition(300, 100))
    workflow.add_node(node2)

    # Create edge: Researcher -> Writer
    edge = WorkflowEdge("researcher", "writer")
    workflow.add_edge(edge)

    return workflow


def create_circular_workflow() -> WorkflowGraph:
    """Create a workflow with 3 agents in a circle."""
    workflow = WorkflowGraph()

    # Create 3 agents
    for i in range(3):
        agent = AgentConfig(
            id=f"agent{i}",
            name=f"Agent {i}",
            provider="mock",
            model="mock-model",
            system_prompt=f"You are agent {i}.",
            temperature=0.7
        )
        node = WorkflowNode(agent, VisualPosition(100 + i * 200, 100))
        workflow.add_node(node)

    # Create circular edges
    workflow.add_edge(WorkflowEdge("agent0", "agent1"))
    workflow.add_edge(WorkflowEdge("agent1", "agent2"))
    workflow.add_edge(WorkflowEdge("agent2", "agent0"))  # Circle back

    return workflow


async def test_basic_execution():
    """Test basic execution with 2 agents."""
    print("\n=== Test: Basic Execution (2 agents) ===\n")

    # Create workflow
    workflow = create_test_workflow()

    # Create provider factory
    providers = {}

    def provider_factory(provider_name: str, model: str):
        if provider_name not in providers:
            providers[provider_name] = MockProvider(name=provider_name)
        return providers[provider_name]

    # Create and initialize engine
    engine = ExecutionEngine(workflow, provider_factory)
    await engine.initialize()

    # Add message callback to log messages
    def message_callback(msg: Message):
        print(f"  Message logged: {msg.sender_id} -> {msg.recipient_id}")

    engine.add_message_callback(message_callback)

    # Create initial message
    initial_message = Message(
        id=str(uuid.uuid4()),
        sender_id="user",
        recipient_id="researcher",
        content="What are the benefits of agent-based systems?",
        timestamp=time.time(),
        metadata={}
    )

    # Start execution in background
    execution_task = asyncio.create_task(engine.start([initial_message]))

    # Let it run for a bit
    await asyncio.sleep(2)

    # Stop execution
    await engine.stop()

    # Cancel execution task
    execution_task.cancel()
    try:
        await execution_task
    except asyncio.CancelledError:
        pass

    # Check results
    message_log = engine.get_message_log()
    stats = engine.get_statistics()

    print(f"\nResults:")
    print(f"  Total messages: {stats['total_messages']}")
    print(f"  Total tokens: {stats['total_tokens']}")
    print(f"  Message flow:")
    for msg in message_log:
        print(f"    {msg.sender_id} -> {msg.recipient_id}: {msg.content[:50]}...")

    assert stats['total_messages'] >= 2, "Should have at least 2 messages"
    print("\n✓ Basic execution test passed!")


async def test_circular_execution():
    """Test execution with circular message flow."""
    print("\n=== Test: Circular Execution (3 agents) ===\n")

    # Create circular workflow
    workflow = create_circular_workflow()

    # Create provider factory
    def provider_factory(provider_name: str, model: str):
        return MockProvider(name=f"mock-{provider_name}")

    # Create and initialize engine
    engine = ExecutionEngine(workflow, provider_factory)
    await engine.initialize()

    # Create initial message
    initial_message = Message(
        id=str(uuid.uuid4()),
        sender_id="user",
        recipient_id="agent0",
        content="Start the conversation",
        timestamp=time.time(),
        metadata={}
    )

    # Start execution in background
    execution_task = asyncio.create_task(engine.start([initial_message]))

    # Let it run for a bit
    await asyncio.sleep(3)

    # Stop execution
    await engine.stop()

    # Cancel execution task
    execution_task.cancel()
    try:
        await execution_task
    except asyncio.CancelledError:
        pass

    # Check results
    stats = engine.get_statistics()

    print(f"\nResults:")
    print(f"  Total messages: {stats['total_messages']}")
    print(f"  Message flow shows circular propagation")

    assert stats['total_messages'] >= 3, "Should have messages from circular flow"
    print("\n✓ Circular execution test passed!")


async def test_message_routing():
    """Test message routing between agents."""
    print("\n=== Test: Message Routing ===\n")

    workflow = create_test_workflow()

    # Create engine
    engine = ExecutionEngine(workflow, lambda p, m: MockProvider(name=p))
    await engine.initialize()

    # Test channel creation
    assert len(engine.channels) == 1, "Should have 1 channel"
    assert ("researcher", "writer") in engine.channels, "Should have researcher->writer channel"

    print(f"  Channels created: {list(engine.channels.keys())}")
    print("\n✓ Message routing test passed!")


async def test_statistics():
    """Test statistics collection."""
    print("\n=== Test: Statistics Collection ===\n")

    workflow = create_test_workflow()
    engine = ExecutionEngine(workflow, lambda p, m: MockProvider())
    await engine.initialize()

    # Create initial message
    initial_message = Message(
        id=str(uuid.uuid4()),
        sender_id="user",
        recipient_id="researcher",
        content="Test message",
        timestamp=time.time(),
        metadata={}
    )

    # Start and stop quickly
    execution_task = asyncio.create_task(engine.start([initial_message]))
    await asyncio.sleep(1)
    await engine.stop()
    execution_task.cancel()
    try:
        await execution_task
    except asyncio.CancelledError:
        pass

    # Check statistics
    stats = engine.get_statistics()

    print(f"  Statistics:")
    print(f"    Total messages: {stats['total_messages']}")
    print(f"    Total tokens: {stats['total_tokens']}")
    print(f"    Agents: {stats['agents']}")
    print(f"    Channels: {stats['channels']}")

    assert stats['agents'] == 2, "Should have 2 agents"
    assert stats['channels'] == 1, "Should have 1 channel"
    print("\n✓ Statistics test passed!")


async def main():
    """Run all execution tests."""
    print("\n" + "=" * 60)
    print("  Testing Phase 2: Execution Engine")
    print("=" * 60)

    try:
        await test_message_routing()
        await test_basic_execution()
        await test_circular_execution()
        await test_statistics()

        print("\n" + "=" * 60)
        print("  ✓ All Phase 2 tests passed!")
        print("=" * 60)
        print("\nPhase 2 is complete. Execution engine is working correctly.")
        print("\nNext steps:")
        print("  - Implement Phase 3: UI Enhancement")
        print("    - Enhanced canvas with configuration dialogs")
        print("    - Execution monitor panel")
        print("    - Integration with simple_canvas.py")

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}\n")
        raise
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}\n")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(main())
