import { useEffect, useState } from 'react';
import { useStore } from '../store';
import * as api from '../api';

export default function AgentConfigModal() {
  const configModalAgentId = useStore(s => s.configModalAgentId);
  const setConfigModalAgentId = useStore(s => s.setConfigModalAgentId);
  const agents = useStore(s => s.agents);
  const updateAgent = useStore(s => s.updateAgent);
  const removeAgent = useStore(s => s.removeAgent);

  const [providers, setProviders] = useState<Record<string, string[]>>({});
  const [form, setForm] = useState({
    name: '', provider: 'anthropic', model: '', system_prompt: '',
    temperature: 0.7, max_tokens: 4096,
  });

  useEffect(() => {
    api.listProviders().then(setProviders);
  }, []);

  useEffect(() => {
    if (configModalAgentId && agents[configModalAgentId]) {
      const a = agents[configModalAgentId];
      setForm({
        name: a.name, provider: a.provider, model: a.model,
        system_prompt: a.system_prompt, temperature: a.temperature,
        max_tokens: a.max_tokens,
      });
    }
  }, [configModalAgentId, agents]);

  if (!configModalAgentId) return null;

  const models = providers[form.provider] || [];

  const handleSave = async () => {
    await updateAgent(configModalAgentId, form);
    setConfigModalAgentId(null);
  };

  const handleDelete = async () => {
    await removeAgent(configModalAgentId);
    setConfigModalAgentId(null);
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setConfigModalAgentId(null)}>
      <div className="bg-white rounded-xl shadow-2xl w-[520px] max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        <div className="px-6 py-4 border-b border-slate-200">
          <h2 className="text-lg font-semibold text-gray-900">Configure Agent</h2>
        </div>

        <div className="px-6 py-4 space-y-4">
          {/* Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
            <input
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
              value={form.name}
              onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
            />
          </div>

          {/* Provider */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Provider</label>
            <div className="flex gap-3">
              {['anthropic', 'openai', 'local'].map(p => (
                <label key={p} className="flex items-center gap-1.5 text-sm">
                  <input
                    type="radio" name="provider" value={p}
                    checked={form.provider === p}
                    onChange={() => setForm(f => ({
                      ...f, provider: p, model: (providers[p] || [])[0] || '',
                    }))}
                    className="accent-purple-600"
                  />
                  {p}
                </label>
              ))}
            </div>
          </div>

          {/* Model */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Model</label>
            <select
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
              value={form.model}
              onChange={e => setForm(f => ({ ...f, model: e.target.value }))}
            >
              {models.map(m => <option key={m} value={m}>{m}</option>)}
            </select>
          </div>

          {/* System Prompt */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">System Prompt</label>
            <textarea
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 h-32 resize-y"
              value={form.system_prompt}
              onChange={e => setForm(f => ({ ...f, system_prompt: e.target.value }))}
            />
          </div>

          {/* Temperature */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Temperature: {form.temperature.toFixed(1)}
            </label>
            <input
              type="range" min="0" max="2" step="0.1"
              className="w-full accent-purple-600"
              value={form.temperature}
              onChange={e => setForm(f => ({ ...f, temperature: parseFloat(e.target.value) }))}
            />
          </div>

          {/* Max Tokens */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Max Tokens</label>
            <input
              type="number" min="1" max="128000"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
              value={form.max_tokens}
              onChange={e => setForm(f => ({ ...f, max_tokens: parseInt(e.target.value) || 4096 }))}
            />
          </div>
        </div>

        <div className="px-6 py-4 border-t border-slate-200 flex justify-between">
          <button
            className="px-4 py-2 text-sm text-red-600 hover:bg-red-50 rounded-lg transition-colors"
            onClick={handleDelete}
          >
            Delete Agent
          </button>
          <div className="flex gap-2">
            <button
              className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
              onClick={() => setConfigModalAgentId(null)}
            >
              Cancel
            </button>
            <button
              className="px-4 py-2 text-sm bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
              onClick={handleSave}
            >
              Save
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
