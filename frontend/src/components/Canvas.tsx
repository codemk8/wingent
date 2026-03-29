import { useCallback, useEffect, useMemo } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  addEdge,
  useNodesState,
  useEdgesState,
  type Connection,
  type Node,
  type Edge,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import AgentNode from './AgentNode';
import { useStore } from '../store';
import { PROVIDER_COLORS } from '../types';

const nodeTypes = { agent: AgentNode };

export default function Canvas() {
  const agents = useStore(s => s.agents);
  const tasks = useStore(s => s.tasks);
  const isRunning = useStore(s => s.isRunning);

  // Build nodes from agent configs
  const agentNodes: Node[] = useMemo(() =>
    Object.values(agents).map(a => ({
      id: a.id,
      type: 'agent',
      position: a.position || { x: 250, y: 250 },
      data: { ...a },
    })),
    [agents]
  );

  // Build task nodes during execution
  const taskNodes: Node[] = useMemo(() => {
    if (!isRunning && Object.keys(tasks).length === 0) return [];
    return Object.values(tasks).map((t, i) => ({
      id: `task-${t.id}`,
      type: 'default',
      position: { x: 100 + (i % 4) * 220, y: 400 + Math.floor(i / 4) * 120 },
      data: {
        label: (
          <div className="text-xs">
            <div className="font-semibold truncate">{t.goal.slice(0, 40)}</div>
            <div className={`inline-block mt-1 px-1.5 py-0.5 rounded text-[10px] ${
              t.status === 'completed' ? 'bg-green-100 text-green-700' :
              t.status === 'failed' ? 'bg-red-100 text-red-700' :
              t.status === 'in_progress' ? 'bg-blue-100 text-blue-700' :
              t.status === 'decomposed' ? 'bg-purple-100 text-purple-700' :
              'bg-gray-100 text-gray-700'
            }`}>{t.status}</div>
          </div>
        ),
      },
      style: {
        border: `2px solid ${
          t.status === 'completed' ? '#10B981' :
          t.status === 'failed' ? '#EF4444' :
          t.status === 'in_progress' ? '#3B82F6' :
          t.status === 'decomposed' ? '#8B5CF6' : '#9CA3AF'
        }`,
        borderRadius: '8px',
        background: 'white',
      },
    }));
  }, [tasks, isRunning]);

  // Task edges (parent → child)
  const taskEdges: Edge[] = useMemo(() => {
    return Object.values(tasks)
      .filter(t => t.parent_task_id)
      .map(t => ({
        id: `te-${t.parent_task_id}-${t.id}`,
        source: `task-${t.parent_task_id}`,
        target: `task-${t.id}`,
        animated: t.status === 'in_progress',
        style: { stroke: '#8B5CF6' },
      }));
  }, [tasks]);

  const allNodes = useMemo(() => [...agentNodes, ...taskNodes], [agentNodes, taskNodes]);
  const allEdges = useMemo(() => [...taskEdges], [taskEdges]);

  const [nodes, setNodes, onNodesChange] = useNodesState(allNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(allEdges);

  useEffect(() => { setNodes(allNodes); }, [allNodes, setNodes]);
  useEffect(() => { setEdges(allEdges); }, [allEdges, setEdges]);

  const onConnect = useCallback(
    (params: Connection) => setEdges(eds => addEdge(params, eds)),
    [setEdges]
  );

  return (
    <div className="flex-1 h-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        nodeTypes={nodeTypes}
        fitView
        className="bg-slate-50"
      >
        <Background color="#e2e8f0" gap={20} />
        <Controls />
        <MiniMap
          nodeColor={(node) => {
            const provider = (node.data as Record<string, unknown>)?.provider as string;
            return PROVIDER_COLORS[provider] || '#6366F1';
          }}
          className="!bg-white !border-slate-200"
        />
      </ReactFlow>
    </div>
  );
}
