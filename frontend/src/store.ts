import { create } from 'zustand';
import type { AgentConfig, Task, ExecutionEvent } from './types';
import * as api from './api';

interface Store {
  // Agents (design-time)
  agents: Record<string, AgentConfig>;
  loadAgents: () => Promise<void>;
  addAgent: (data: Partial<AgentConfig>) => Promise<AgentConfig>;
  updateAgent: (id: string, data: Partial<AgentConfig>) => Promise<void>;
  removeAgent: (id: string) => Promise<void>;
  applyTopology: (name: string) => Promise<void>;

  // Tasks (runtime)
  tasks: Record<string, Task>;
  events: ExecutionEvent[];
  isRunning: boolean;
  submitTask: (goal: string, criteria: string, agentId?: string) => Promise<void>;
  stopExecution: () => Promise<void>;
  refreshTasks: () => Promise<void>;

  // WebSocket
  ws: WebSocket | null;
  connectWs: () => void;
  disconnectWs: () => void;

  // UI state
  selectedAgentId: string | null;
  setSelectedAgentId: (id: string | null) => void;
  configModalAgentId: string | null;
  setConfigModalAgentId: (id: string | null) => void;
  showTaskModal: boolean;
  setShowTaskModal: (show: boolean) => void;
}

export const useStore = create<Store>((set, get) => ({
  // Agents
  agents: {},
  loadAgents: async () => {
    const list = await api.listAgents();
    const agents: Record<string, AgentConfig> = {};
    list.forEach(a => { agents[a.id] = a; });
    set({ agents });
  },
  addAgent: async (data) => {
    const agent = await api.createAgent(data);
    set(s => ({ agents: { ...s.agents, [agent.id]: agent } }));
    return agent;
  },
  updateAgent: async (id, data) => {
    const agent = await api.updateAgent(id, { ...get().agents[id], ...data });
    set(s => ({ agents: { ...s.agents, [id]: agent } }));
  },
  removeAgent: async (id) => {
    await api.deleteAgent(id);
    set(s => {
      const agents = { ...s.agents };
      delete agents[id];
      return { agents };
    });
  },
  applyTopology: async (name) => {
    const agents = await api.applyTopology(name);
    const map: Record<string, AgentConfig> = {};
    agents.forEach(a => { map[a.id] = a; });
    set({ agents: map });
  },

  // Tasks
  tasks: {},
  events: [],
  isRunning: false,
  submitTask: async (goal, criteria, agentId) => {
    set({ tasks: {}, events: [], isRunning: true });
    await api.submitTask(goal, criteria, agentId);
  },
  stopExecution: async () => {
    await api.stopExecution();
    set({ isRunning: false });
  },
  refreshTasks: async () => {
    const list = await api.listTasks();
    const tasks: Record<string, Task> = {};
    list.forEach(t => { tasks[t.id] = t; });
    set({ tasks });
  },

  // WebSocket
  ws: null,
  connectWs: () => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      const event: ExecutionEvent = {
        event: msg.event,
        data: msg.data,
        timestamp: Date.now(),
      };
      set(s => ({ events: [...s.events, event] }));

      // Refresh tasks on significant events
      if (['task_started', 'subtask_spawned', 'task_completed', 'task_failed', 'turn_completed'].includes(msg.event)) {
        get().refreshTasks();
      }
      if (msg.event === 'task_completed' || msg.event === 'task_failed') {
        // Check if root task is done
        const tasks = get().tasks;
        const roots = Object.values(tasks).filter(t => !t.parent_task_id);
        if (roots.length > 0 && roots.every(t => t.status === 'completed' || t.status === 'failed')) {
          set({ isRunning: false });
        }
      }
    };
    ws.onclose = () => set({ ws: null });
    set({ ws });
  },
  disconnectWs: () => {
    get().ws?.close();
    set({ ws: null });
  },

  // UI state
  selectedAgentId: null,
  setSelectedAgentId: (id) => set({ selectedAgentId: id }),
  configModalAgentId: null,
  setConfigModalAgentId: (id) => set({ configModalAgentId: id }),
  showTaskModal: false,
  setShowTaskModal: (show) => set({ showTaskModal: show }),
}));
