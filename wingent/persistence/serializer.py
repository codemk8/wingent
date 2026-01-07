"""
Workflow serialization to/from JSON.
"""

import json
from typing import Dict, Any
from ..app.workflow import WorkflowGraph, WorkflowNode, WorkflowEdge
from ..core.agent import AgentConfig, VisualPosition


class WorkflowSerializer:
    """Handles serialization/deserialization of workflows."""

    @staticmethod
    def to_json(workflow: WorkflowGraph, filepath: str):
        """
        Save workflow to JSON file.

        Args:
            workflow: WorkflowGraph to save
            filepath: Path to JSON file
        """
        data = workflow.to_dict()

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def from_json(filepath: str) -> WorkflowGraph:
        """
        Load workflow from JSON file.

        Args:
            filepath: Path to JSON file

        Returns:
            WorkflowGraph instance
        """
        with open(filepath, "r") as f:
            data = json.load(f)

        return WorkflowGraph.from_dict(data)
