"""
Workflow graph data structures.
"""

from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional
from ..core.agent import AgentConfig, VisualPosition


@dataclass
class WorkflowNode:
    """Node in the workflow graph."""
    agent_config: AgentConfig
    position: VisualPosition

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "agent_config": self.agent_config.to_dict(),
            "position": self.position.to_dict()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowNode':
        """Create from dictionary."""
        return cls(
            agent_config=AgentConfig.from_dict(data["agent_config"]),
            position=VisualPosition.from_dict(data["position"])
        )


@dataclass
class WorkflowEdge:
    """Edge/link in the workflow graph."""
    source_id: str
    target_id: str

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for serialization."""
        return {
            "source": self.source_id,
            "target": self.target_id
        }

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'WorkflowEdge':
        """Create from dictionary."""
        return cls(
            source_id=data["source"],
            target_id=data["target"]
        )


class WorkflowGraph:
    """Complete workflow definition."""

    def __init__(self):
        """Initialize empty workflow graph."""
        self.nodes: Dict[str, WorkflowNode] = {}
        self.edges: List[WorkflowEdge] = []
        self.metadata: Dict[str, Any] = {}

    def add_node(self, node: WorkflowNode):
        """
        Add agent node to graph.

        Args:
            node: WorkflowNode to add

        Raises:
            ValueError: If node with same ID already exists
        """
        node_id = node.agent_config.id
        if node_id in self.nodes:
            raise ValueError(f"Node with ID '{node_id}' already exists")
        self.nodes[node_id] = node

    def remove_node(self, node_id: str):
        """
        Remove node from graph and all connected edges.

        Args:
            node_id: ID of node to remove

        Raises:
            ValueError: If node doesn't exist
        """
        if node_id not in self.nodes:
            raise ValueError(f"Node with ID '{node_id}' doesn't exist")

        # Remove node
        del self.nodes[node_id]

        # Remove all edges connected to this node
        self.edges = [
            edge for edge in self.edges
            if edge.source_id != node_id and edge.target_id != node_id
        ]

    def add_edge(self, edge: WorkflowEdge):
        """
        Add communication channel.

        Args:
            edge: WorkflowEdge to add

        Raises:
            ValueError: If edge already exists or nodes don't exist
        """
        # Check if nodes exist
        if edge.source_id not in self.nodes:
            raise ValueError(f"Source node '{edge.source_id}' doesn't exist")
        if edge.target_id not in self.nodes:
            raise ValueError(f"Target node '{edge.target_id}' doesn't exist")

        # Check if edge already exists
        for existing_edge in self.edges:
            if (existing_edge.source_id == edge.source_id and
                existing_edge.target_id == edge.target_id):
                raise ValueError(
                    f"Edge from '{edge.source_id}' to '{edge.target_id}' already exists"
                )

        self.edges.append(edge)

    def remove_edge(self, source_id: str, target_id: str):
        """
        Remove edge from graph.

        Args:
            source_id: Source node ID
            target_id: Target node ID

        Raises:
            ValueError: If edge doesn't exist
        """
        for i, edge in enumerate(self.edges):
            if edge.source_id == source_id and edge.target_id == target_id:
                del self.edges[i]
                return

        raise ValueError(f"Edge from '{source_id}' to '{target_id}' doesn't exist")

    def get_node(self, node_id: str) -> Optional[WorkflowNode]:
        """
        Get node by ID.

        Args:
            node_id: Node ID

        Returns:
            WorkflowNode if found, None otherwise
        """
        return self.nodes.get(node_id)

    def get_outgoing_edges(self, node_id: str) -> List[WorkflowEdge]:
        """
        Get all edges going out from a node.

        Args:
            node_id: Node ID

        Returns:
            List of outgoing edges
        """
        return [edge for edge in self.edges if edge.source_id == node_id]

    def get_incoming_edges(self, node_id: str) -> List[WorkflowEdge]:
        """
        Get all edges coming into a node.

        Args:
            node_id: Node ID

        Returns:
            List of incoming edges
        """
        return [edge for edge in self.edges if edge.target_id == node_id]

    def validate(self) -> List[str]:
        """
        Validate graph structure.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Check for orphaned edges (edges referencing non-existent nodes)
        for edge in self.edges:
            if edge.source_id not in self.nodes:
                errors.append(f"Edge references non-existent source node: {edge.source_id}")
            if edge.target_id not in self.nodes:
                errors.append(f"Edge references non-existent target node: {edge.target_id}")

        # Check for self-loops
        for edge in self.edges:
            if edge.source_id == edge.target_id:
                errors.append(f"Self-loop detected on node: {edge.source_id}")

        # Warn about cycles (optional - cycles may be intentional)
        cycles = self._detect_cycles()
        if cycles:
            errors.append(f"Cycles detected in graph: {cycles}")

        return errors

    def _detect_cycles(self) -> List[List[str]]:
        """
        Detect cycles in the graph using DFS.

        Returns:
            List of cycles (each cycle is a list of node IDs)
        """
        def dfs(node_id: str, visited: set, path: list) -> List[List[str]]:
            if node_id in path:
                # Found a cycle
                cycle_start = path.index(node_id)
                return [path[cycle_start:] + [node_id]]

            if node_id in visited:
                return []

            visited.add(node_id)
            path.append(node_id)

            cycles = []
            for edge in self.get_outgoing_edges(node_id):
                cycles.extend(dfs(edge.target_id, visited, path.copy()))

            return cycles

        all_cycles = []
        visited = set()

        for node_id in self.nodes:
            if node_id not in visited:
                all_cycles.extend(dfs(node_id, visited, []))

        return all_cycles

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize to dictionary for JSON storage.

        Returns:
            Dictionary representation
        """
        return {
            "version": "1.0",
            "metadata": self.metadata,
            "nodes": [node.to_dict() for node in self.nodes.values()],
            "edges": [edge.to_dict() for edge in self.edges]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowGraph':
        """
        Deserialize from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            WorkflowGraph instance
        """
        workflow = cls()
        workflow.metadata = data.get("metadata", {})

        # Load nodes
        for node_data in data.get("nodes", []):
            node = WorkflowNode.from_dict(node_data)
            workflow.nodes[node.agent_config.id] = node

        # Load edges
        for edge_data in data.get("edges", []):
            edge = WorkflowEdge.from_dict(edge_data)
            workflow.edges.append(edge)

        return workflow

    def __repr__(self) -> str:
        """String representation."""
        return f"WorkflowGraph(nodes={len(self.nodes)}, edges={len(self.edges)})"
