import { Handle, Position, type NodeProps } from '@xyflow/react';
import type { AgentConfig } from '../types';
import { PROVIDER_COLORS } from '../types';
import { useStore } from '../store';

type AgentNodeData = AgentConfig & { label?: string };

export default function AgentNode({ data, id }: NodeProps) {
  const d = data as unknown as AgentNodeData;
  const setConfigModalAgentId = useStore(s => s.setConfigModalAgentId);
  const borderColor = PROVIDER_COLORS[d.provider] || '#6366F1';

  return (
    <div
      className="bg-white rounded-lg shadow-md border-2 px-3 py-2 min-w-[180px] cursor-pointer hover:shadow-lg transition-shadow"
      style={{ borderColor }}
      onDoubleClick={() => setConfigModalAgentId(id)}
    >
      <Handle type="target" position={Position.Left} className="!bg-gray-400 !w-2 !h-2" />

      <div className="flex items-center justify-between mb-1">
        <span className="font-semibold text-sm text-gray-900 truncate">{d.name}</span>
        <span
          className="text-[10px] px-1.5 py-0.5 rounded-full text-white font-medium"
          style={{ backgroundColor: borderColor }}
        >
          {d.provider}
        </span>
      </div>

      <div className="text-xs text-gray-500 truncate">{d.model}</div>

      <div className="flex items-center justify-between mt-1.5">
        <span className="text-[10px] text-gray-400">temp: {d.temperature}</span>
        <button
          className="text-gray-400 hover:text-gray-600 text-xs"
          onClick={(e) => { e.stopPropagation(); setConfigModalAgentId(id); }}
        >
          config
        </button>
      </div>

      <Handle type="source" position={Position.Right} className="!bg-gray-400 !w-2 !h-2" />
    </div>
  );
}
