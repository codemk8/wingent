#!/usr/bin/env python3
"""
Test workflow creation and save/load functionality.
"""

from wingent.app.workflow import WorkflowGraph, WorkflowNode, WorkflowEdge
from wingent.core.agent import AgentConfig, VisualPosition
from wingent.persistence.serializer import WorkflowSerializer


def create_test_workflow():
    """Create a test workflow."""
    workflow = WorkflowGraph()
    workflow.metadata = {
        "name": "Research and Writing Pipeline",
        "description": "A multi-agent workflow for research and content creation",
        "version": "1.0"
    }

    # Agent 1: Researcher
    researcher = AgentConfig(
        id="researcher",
        name="Research Specialist",
        provider="anthropic",
        model="claude-sonnet-4-5-20250929",
        system_prompt="You are an expert researcher. Analyze questions deeply and provide well-researched, factual insights with citations when possible.",
        temperature=0.7,
        max_tokens=2000
    )
    workflow.add_node(WorkflowNode(researcher, VisualPosition(100, 100)))

    # Agent 2: Writer
    writer = AgentConfig(
        id="writer",
        name="Content Writer",
        provider="anthropic",
        model="claude-sonnet-4-5-20250929",
        system_prompt="You are a professional writer. Transform research into engaging, clear, and well-structured content.",
        temperature=0.8,
        max_tokens=2000
    )
    workflow.add_node(WorkflowNode(writer, VisualPosition(400, 100)))

    # Agent 3: Editor
    editor = AgentConfig(
        id="editor",
        name="Editor",
        provider="anthropic",
        model="claude-3-5-haiku-20241022",
        system_prompt="You are a meticulous editor. Review content for clarity, grammar, style, and impact. Provide constructive feedback.",
        temperature=0.6,
        max_tokens=1500
    )
    workflow.add_node(WorkflowNode(editor, VisualPosition(700, 100)))

    # Agent 4: Fact Checker
    fact_checker = AgentConfig(
        id="fact_checker",
        name="Fact Checker",
        provider="anthropic",
        model="claude-3-5-haiku-20241022",
        system_prompt="You are a fact checker. Verify claims and ensure accuracy. Flag any questionable statements.",
        temperature=0.3,
        max_tokens=1000
    )
    workflow.add_node(WorkflowNode(fact_checker, VisualPosition(400, 300)))

    # Links
    workflow.add_edge(WorkflowEdge("researcher", "writer"))
    workflow.add_edge(WorkflowEdge("writer", "editor"))
    workflow.add_edge(WorkflowEdge("researcher", "fact_checker"))
    workflow.add_edge(WorkflowEdge("fact_checker", "editor"))

    return workflow


def test_save_load():
    """Test save and load functionality."""
    print("Creating test workflow...")
    workflow = create_test_workflow()

    print(f"Workflow has {len(workflow.nodes)} agents and {len(workflow.edges)} links")

    # Validate
    errors = workflow.validate()
    if errors:
        print(f"Validation errors: {errors}")
    else:
        print("✓ Workflow validation passed")

    # Save
    filename = "examples/research_pipeline.json"
    print(f"\nSaving to {filename}...")
    WorkflowSerializer.to_json(workflow, filename)
    print("✓ Saved successfully")

    # Load
    print(f"\nLoading from {filename}...")
    loaded_workflow = WorkflowSerializer.from_json(filename)
    print(f"✓ Loaded workflow with {len(loaded_workflow.nodes)} agents")

    # Verify
    assert len(loaded_workflow.nodes) == len(workflow.nodes)
    assert len(loaded_workflow.edges) == len(workflow.edges)
    print("✓ Verification passed")

    print("\n" + "="*60)
    print("Test completed successfully!")
    print("="*60)
    print(f"\nYou can now open '{filename}' in the Wingent GUI:")
    print("  File > Open > examples/research_pipeline.json")


if __name__ == "__main__":
    import os
    os.makedirs("examples", exist_ok=True)
    test_save_load()
