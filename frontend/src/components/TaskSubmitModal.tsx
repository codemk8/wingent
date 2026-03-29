import { useState } from 'react';
import { useStore } from '../store';

export default function TaskSubmitModal() {
  const showTaskModal = useStore(s => s.showTaskModal);
  const setShowTaskModal = useStore(s => s.setShowTaskModal);
  const agents = useStore(s => s.agents);
  const submitTask = useStore(s => s.submitTask);

  const [goal, setGoal] = useState('');
  const [criteria, setCriteria] = useState('');
  const [agentId, setAgentId] = useState('');

  if (!showTaskModal) return null;

  const agentList = Object.values(agents);

  const handleSubmit = async () => {
    if (!goal.trim()) return;
    await submitTask(goal, criteria, agentId || undefined);
    setGoal('');
    setCriteria('');
    setShowTaskModal(false);
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setShowTaskModal(false)}>
      <div className="bg-white rounded-xl shadow-2xl w-[480px]" onClick={e => e.stopPropagation()}>
        <div className="px-6 py-4 border-b border-slate-200">
          <h2 className="text-lg font-semibold text-gray-900">Submit Task</h2>
        </div>

        <div className="px-6 py-4 space-y-4">
          {/* Goal */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Goal</label>
            <textarea
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 h-24 resize-y"
              placeholder="What should the agent accomplish?"
              value={goal}
              onChange={e => setGoal(e.target.value)}
            />
          </div>

          {/* Completion Criteria */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Completion Criteria</label>
            <textarea
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 h-20 resize-y"
              placeholder="How do we know when the task is done?"
              value={criteria}
              onChange={e => setCriteria(e.target.value)}
            />
          </div>

          {/* Agent Selection */}
          {agentList.length > 0 && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Agent</label>
              <select
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                value={agentId}
                onChange={e => setAgentId(e.target.value)}
              >
                <option value="">Auto (first available)</option>
                {agentList.map(a => (
                  <option key={a.id} value={a.id}>{a.name} ({a.provider})</option>
                ))}
              </select>
            </div>
          )}
        </div>

        <div className="px-6 py-4 border-t border-slate-200 flex justify-end gap-2">
          <button
            className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
            onClick={() => setShowTaskModal(false)}
          >
            Cancel
          </button>
          <button
            className="px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50"
            onClick={handleSubmit}
            disabled={!goal.trim()}
          >
            Submit
          </button>
        </div>
      </div>
    </div>
  );
}
