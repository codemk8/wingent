import { useState } from 'react';
import { useStore } from '../store';

export default function Landing() {
  const submitTask = useStore(s => s.submitTask);
  const [goal, setGoal] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [workingDir, setWorkingDir] = useState('');
  const [provider, setProvider] = useState('anthropic');
  const [model, setModel] = useState('claude-sonnet-4-5-20250929');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const providerModels: Record<string, string[]> = {
    anthropic: ['claude-sonnet-4-5-20250929', 'claude-opus-4-5-20251101', 'claude-3-5-haiku-20241022'],
    openai: ['gpt-4-turbo', 'gpt-4', 'gpt-3.5-turbo'],
    local: ['llama3', 'mistral', 'codellama'],
  };

  const handleSubmit = async () => {
    if (!goal.trim()) return;
    setSubmitting(true);
    setError('');
    try {
      await submitTask({
        goal: goal.trim(),
        working_directory: workingDir.trim() || undefined,
        provider,
        model,
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to submit task');
      setSubmitting(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      handleSubmit();
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center p-4">
      <div className="w-full max-w-2xl">
        {/* Logo / Title */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-slate-900 mb-2">Wingent</h1>
          <p className="text-slate-500 text-lg">Describe what you need done. Agents will figure out the rest.</p>
        </div>

        {/* Main Input Card */}
        <div className="bg-white rounded-2xl shadow-lg border border-slate-200 overflow-hidden">
          {/* Task Input */}
          <div className="p-6">
            <label className="block text-sm font-medium text-slate-700 mb-2">
              What do you want to accomplish?
            </label>
            <textarea
              className="w-full px-4 py-3 border border-slate-300 rounded-xl text-base focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none h-32 placeholder-slate-400"
              placeholder="e.g., Analyze the codebase and write a summary of the architecture..."
              value={goal}
              onChange={e => setGoal(e.target.value)}
              onKeyDown={handleKeyDown}
              autoFocus
            />
          </div>

          {/* Advanced Options Toggle */}
          <div className="px-6">
            <button
              className="text-sm text-slate-500 hover:text-slate-700 flex items-center gap-1"
              onClick={() => setShowAdvanced(!showAdvanced)}
            >
              <span className={`transition-transform ${showAdvanced ? 'rotate-90' : ''}`}>&#9654;</span>
              Options
            </button>
          </div>

          {/* Advanced Options */}
          {showAdvanced && (
            <div className="px-6 pt-3 pb-1 space-y-4 border-t border-slate-100 mt-3">
              {/* Working Directory */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Working Directory
                  <span className="text-slate-400 font-normal ml-1">(optional)</span>
                </label>
                <input
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                  placeholder="/path/to/project"
                  value={workingDir}
                  onChange={e => setWorkingDir(e.target.value)}
                />
                <p className="text-xs text-slate-400 mt-1">
                  Give agents context about a specific directory to work with.
                </p>
              </div>

              {/* Provider + Model */}
              <div className="flex gap-4">
                <div className="flex-1">
                  <label className="block text-sm font-medium text-slate-700 mb-1">Provider</label>
                  <select
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                    value={provider}
                    onChange={e => {
                      const p = e.target.value;
                      setProvider(p);
                      setModel(providerModels[p]?.[0] || '');
                    }}
                  >
                    <option value="anthropic">Anthropic</option>
                    <option value="openai">OpenAI</option>
                    <option value="local">Local (Ollama)</option>
                  </select>
                </div>
                <div className="flex-1">
                  <label className="block text-sm font-medium text-slate-700 mb-1">Model</label>
                  <select
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                    value={model}
                    onChange={e => setModel(e.target.value)}
                  >
                    {(providerModels[provider] || []).map(m => (
                      <option key={m} value={m}>{m}</option>
                    ))}
                  </select>
                </div>
              </div>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="mx-6 mt-3 px-4 py-2 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
              {error}
            </div>
          )}

          {/* Submit */}
          <div className="p-6 pt-4">
            <button
              className="w-full py-3 bg-purple-600 text-white rounded-xl font-medium text-base hover:bg-purple-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              onClick={handleSubmit}
              disabled={!goal.trim() || submitting}
            >
              {submitting ? 'Starting...' : 'Start'}
            </button>
            <p className="text-xs text-slate-400 text-center mt-2">
              Press <kbd className="px-1.5 py-0.5 bg-slate-100 rounded text-slate-500 font-mono">Cmd+Enter</kbd> to submit
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
