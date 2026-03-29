import { useEffect, useState } from 'react';
import { useStore } from '../store';
import * as api from '../api';

type Tab = 'topologies' | 'agents';

export default function Sidebar() {
  const [tab, setTab] = useState<Tab>('topologies');
  const [topologies, setTopologies] = useState<Record<string, { name: string; description: string }>>({});
  const [templates, setTemplates] = useState<Record<string, { name: string; provider: string; temperature: number }>>({});
  const applyTopology = useStore(s => s.applyTopology);
  const addAgent = useStore(s => s.addAgent);

  useEffect(() => {
    api.listTopologies().then(setTopologies);
    api.listTemplates().then(t => setTemplates(t as Record<string, { name: string; provider: string; temperature: number }>));
  }, []);

  return (
    <div className="w-72 bg-white border-r border-slate-200 flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-3 bg-slate-900 text-white">
        <h1 className="text-lg font-bold">Wingent</h1>
        <p className="text-xs text-slate-400">Multi-Agent Workflow</p>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-200">
        <button
          className={`flex-1 px-3 py-2 text-sm font-medium ${tab === 'topologies' ? 'text-purple-600 border-b-2 border-purple-600' : 'text-gray-500'}`}
          onClick={() => setTab('topologies')}
        >
          Templates
        </button>
        <button
          className={`flex-1 px-3 py-2 text-sm font-medium ${tab === 'agents' ? 'text-purple-600 border-b-2 border-purple-600' : 'text-gray-500'}`}
          onClick={() => setTab('agents')}
        >
          Agent Types
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {tab === 'topologies' && Object.entries(topologies).map(([key, topo]) => (
          <div key={key} className="p-3 border border-slate-200 rounded-lg hover:border-purple-300 hover:bg-purple-50 transition-colors">
            <div className="font-medium text-sm text-gray-900">{topo.name}</div>
            <div className="text-xs text-gray-500 mt-1">{topo.description}</div>
            <button
              className="mt-2 text-xs px-3 py-1 bg-purple-600 text-white rounded hover:bg-purple-700 transition-colors"
              onClick={() => applyTopology(key)}
            >
              Use Template
            </button>
          </div>
        ))}

        {tab === 'agents' && Object.entries(templates).map(([key, tmpl]) => (
          <button
            key={key}
            className="w-full p-3 border border-slate-200 rounded-lg hover:border-green-300 hover:bg-green-50 transition-colors text-left"
            onClick={() => addAgent({
              name: tmpl.name,
              provider: tmpl.provider,
              temperature: tmpl.temperature,
              position: { x: 150 + Math.random() * 300, y: 100 + Math.random() * 300 },
            })}
          >
            <div className="font-medium text-sm text-gray-900">{tmpl.name}</div>
            <div className="text-xs text-gray-500 mt-0.5">{tmpl.provider}</div>
          </button>
        ))}
      </div>
    </div>
  );
}
