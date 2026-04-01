#!/usr/bin/env python3
"""
Test script for Phase 1 core components.
"""

from wingent.core.agent import AgentConfig, VisualPosition
from wingent.app.workflow import WorkflowGraph, WorkflowNode, WorkflowEdge


def test_agent_config():
    """Test AgentConfig creation and serialization."""
    print("Testing AgentConfig...")

    config = AgentConfig(
        id="agent1",
        name="Researcher",
        provider="anthropic",
        model="claude-sonnet-4-5-20250929",
        system_prompt="You are a research assistant.",
        temperature=0.7,
        max_tokens=4096
    )

    # Test to_dict
    data = config.to_dict()
    assert data["id"] == "agent1"
    assert data["name"] == "Researcher"
    assert data["provider"] == "anthropic"

    # Test from_dict
    config2 = AgentConfig.from_dict(data)
    assert config2.id == config.id
    assert config2.name == config.name
    assert config2.provider == config.provider

    print("  ✓ AgentConfig works correctly")


def test_visual_position():
    """Test VisualPosition creation and serialization."""
    print("Testing VisualPosition...")

    pos = VisualPosition(x=100, y=200)

    # Test to_dict
    data = pos.to_dict()
    assert data["x"] == 100
    assert data["y"] == 200

    # Test from_dict
    pos2 = VisualPosition.from_dict(data)
    assert pos2.x == pos.x
    assert pos2.y == pos.y

    print("  ✓ VisualPosition works correctly")


def test_workflow_graph():
    """Test WorkflowGraph creation and operations."""
    print("Testing WorkflowGraph...")

    # Create workflow
    workflow = WorkflowGraph()

    # Create nodes
    agent1 = AgentConfig(
        id="agent1",
        name="Researcher",
        provider="anthropic",
        model="claude-sonnet-4-5-20250929",
        system_prompt="You are a research assistant."
    )

    agent2 = AgentConfig(
        id="agent2",
        name="Writer",
        provider="anthropic",
        model="claude-sonnet-4-5-20250929",
        system_prompt="You are a writer."
    )

    node1 = WorkflowNode(agent1, VisualPosition(100, 100))
    node2 = WorkflowNode(agent2, VisualPosition(300, 100))

    # Add nodes
    workflow.add_node(node1)
    workflow.add_node(node2)

    assert len(workflow.nodes) == 2
    assert workflow.get_node("agent1") is not None

    # Add edge
    edge = WorkflowEdge("agent1", "agent2")
    workflow.add_edge(edge)

    assert len(workflow.edges) == 1

    # Test outgoing/incoming edges
    outgoing = workflow.get_outgoing_edges("agent1")
    assert len(outgoing) == 1
    assert outgoing[0].target_id == "agent2"

    incoming = workflow.get_incoming_edges("agent2")
    assert len(incoming) == 1
    assert incoming[0].source_id == "agent1"

    # Test validation
    errors = workflow.validate()
    assert len(errors) == 0  # Should be valid

    print("  ✓ WorkflowGraph works correctly")


def test_workflow_serialization():
    """Test workflow serialization to dict."""
    print("Testing workflow serialization...")

    # Create workflow
    workflow = WorkflowGraph()
    workflow.metadata = {"created_by": "test", "version": "1.0"}

    # Add nodes
    agent1 = AgentConfig(
        id="agent1",
        name="Agent 1",
        provider="anthropic",
        model="claude-sonnet-4-5-20250929",
        system_prompt="System prompt 1"
    )

    node1 = WorkflowNode(agent1, VisualPosition(50, 100))
    workflow.add_node(node1)

    # Serialize
    data = workflow.to_dict()

    assert data["version"] == "1.0"
    assert len(data["nodes"]) == 1
    assert data["nodes"][0]["agent_config"]["id"] == "agent1"
    assert data["nodes"][0]["position"]["x"] == 50

    # Deserialize
    workflow2 = WorkflowGraph.from_dict(data)

    assert len(workflow2.nodes) == 1
    assert workflow2.get_node("agent1") is not None
    assert workflow2.metadata["created_by"] == "test"

    print("  ✓ Workflow serialization works correctly")


def test_workflow_validation():
    """Test workflow validation."""
    print("Testing workflow validation...")

    workflow = WorkflowGraph()

    # Add nodes
    agent1 = AgentConfig(
        id="agent1",
        name="Agent 1",
        provider="anthropic",
        model="claude-sonnet-4-5-20250929",
        system_prompt="Prompt 1"
    )

    node1 = WorkflowNode(agent1, VisualPosition(100, 100))
    workflow.add_node(node1)

    # Test self-loop detection
    self_loop = WorkflowEdge("agent1", "agent1")
    workflow.edges.append(self_loop)  # Add directly to bypass add_edge validation

    errors = workflow.validate()
    assert len(errors) > 0
    assert any("self-loop" in error.lower() for error in errors)

    print("  ✓ Workflow validation works correctly")


def main():
    """Run all tests."""
    print("\n=== Testing Phase 1: Core Components ===\n")

    try:
        test_agent_config()
        test_visual_position()
        test_workflow_graph()
        test_workflow_serialization()
        test_workflow_validation()

        print("\n✓ All tests passed!\n")
        print("Phase 1 is complete. Core components are working correctly.")
        print("\nNext steps:")
        print("  - Implement Phase 2: Execution Engine (wingent/core/executor.py)")
        print("  - Implement additional providers (OpenAI, local models)")

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}\n")
        raise
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}\n")
        raise


if __name__ == "__main__":
    main()
