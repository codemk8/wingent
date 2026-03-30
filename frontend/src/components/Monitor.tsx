import { useEffect, useRef } from 'react';
import { useStore } from '../store';
import { STATUS_COLORS } from '../types';

export default function Monitor() {
  const tasks = useStore(s => s.tasks);
  const events = useStore(s => s.events);
  const isRunning = useStore(s => s.isRunning);
  const currentGoal = useStore(s => s.currentGoal);
  const stopExecution = useStore(s => s.stopExecution);
  const resetExecution = useStore(s => s.resetExecution);
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [events]);

  const rootTasks = Object.values(tasks).filter(t => !t.parent_task_id);
  const taskList = Object.values(tasks);
  const completed = taskList.filter(t => t.status === 'completed').length;
  const failed = taskList.filter(t => t.status === 'failed').length;

  return (
    <div className="w-96 bg-white border-l border-slate-200 flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-3 bg-slate-900 text-white">
        <div className="flex items-center justify-between mb-1">
          <h2 className="font-semibold text-sm">Execution Monitor</h2>
          <div className="flex gap-2">
            {isRunning ? (
              <button
                className="px-3 py-1 text-xs bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
                onClick={stopExecution}
              >
                Stop
              </button>
            ) : (
              <button
                className="px-3 py-1 text-xs bg-slate-600 text-white rounded hover:bg-slate-500 transition-colors"
                onClick={resetExecution}
              >
                New Task
              </button>
            )}
          </div>
        </div>
        {currentGoal && (
          <p className="text-xs text-slate-400 truncate" title={currentGoal}>{currentGoal}</p>
        )}
      </div>

      {/* Task Tree */}
      <div className="px-3 py-2 border-b border-slate-200">
        <h3 className="text-xs font-semibold text-gray-500 uppercase mb-2">Task Tree</h3>
        {taskList.length === 0 ? (
          <p className="text-xs text-gray-400 italic">No tasks yet. Submit a task to begin.</p>
        ) : (
          <div className="space-y-1 max-h-48 overflow-y-auto">
            {rootTasks.map(t => (
              <TaskNode key={t.id} taskId={t.id} tasks={tasks} depth={0} />
            ))}
          </div>
        )}
      </div>

      {/* Event Log */}
      <div className="flex-1 flex flex-col min-h-0">
        <h3 className="text-xs font-semibold text-gray-500 uppercase px-3 py-2">Event Log</h3>
        <div ref={logRef} className="flex-1 overflow-y-auto px-3 space-y-1 text-xs font-mono">
          {events.map((e, i) => (
            <div key={i} className="py-0.5 border-b border-slate-50">
              <span className="text-gray-400">
                {new Date(e.timestamp).toLocaleTimeString()}
              </span>{' '}
              <span className="text-purple-600 font-semibold">{e.event}</span>{' '}
              <span className="text-gray-600">
                {formatEventData(e.event, e.data)}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Stats */}
      <div className="px-3 py-2 bg-slate-50 border-t border-slate-200 text-xs text-gray-500 flex gap-4">
        <span>Tasks: {taskList.length}</span>
        <span className="text-green-600">Done: {completed}</span>
        <span className="text-red-600">Failed: {failed}</span>
        <span className={isRunning ? 'text-green-600 font-semibold' : 'text-gray-400'}>
          {isRunning ? 'Running' : 'Idle'}
        </span>
      </div>
    </div>
  );
}

function TaskNode({ taskId, tasks, depth }: { taskId: string; tasks: Record<string, import('../types').Task>; depth: number }) {
  const task = tasks[taskId];
  if (!task) return null;

  const statusClass = STATUS_COLORS[task.status] || 'bg-gray-100';

  return (
    <div style={{ marginLeft: depth * 16 }}>
      <div className="flex items-center gap-1.5 py-0.5">
        <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${statusClass}`}>
          {task.status}
        </span>
        <span className="text-xs text-gray-700 truncate flex-1" title={task.goal}>
          {task.goal.slice(0, 50)}
        </span>
      </div>
      {task.result && (
        <div className="text-[10px] text-green-600 ml-4 truncate" title={task.result}>
          {task.result.slice(0, 80)}...
        </div>
      )}
      {task.error && (
        <div className="text-[10px] text-red-600 ml-4 truncate">{task.error}</div>
      )}
      {task.subtask_ids.map(sid => (
        <TaskNode key={sid} taskId={sid} tasks={tasks} depth={depth + 1} />
      ))}
    </div>
  );
}

function formatEventData(event: string, data: Record<string, unknown>): string {
  switch (event) {
    case 'task_started': return `agent=${(data.agent_id as string)?.slice(0, 8)}`;
    case 'turn_completed': return `turn ${data.turn}, ${data.tool_calls} tools`;
    case 'subtask_spawned': return `${(data.goal as string)?.slice(0, 50)}`;
    case 'task_completed': return `${(data.result_preview as string)?.slice(0, 60)}`;
    case 'task_failed': return `${data.error}`;
    case 'manager_started': return `agent=${(data.agent_id as string)?.slice(0, 8)}`;
    default: return JSON.stringify(data).slice(0, 80);
  }
}
