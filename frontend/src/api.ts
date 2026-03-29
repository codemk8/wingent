import type { AgentConfig, Task } from './types';

const BASE = '';

async function json<T>(url: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(BASE + url, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status}: ${body}`);
  }
  return res.json();
}

// Agents
export const listAgents = () => json<AgentConfig[]>('/api/agents');
export const createAgent = (data: Partial<AgentConfig>) =>
  json<AgentConfig>('/api/agents', { method: 'POST', body: JSON.stringify(data) });
export const updateAgent = (id: string, data: Partial<AgentConfig>) =>
  json<AgentConfig>(`/api/agents/${id}`, { method: 'PUT', body: JSON.stringify(data) });
export const deleteAgent = (id: string) =>
  json<{ ok: boolean }>(`/api/agents/${id}`, { method: 'DELETE' });

// Templates
export const listTemplates = () => json<Record<string, unknown>>('/api/agents/templates');
export const listTopologies = () => json<Record<string, { name: string; description: string }>>('/api/agents/topologies');
export const applyTopology = (name: string) =>
  json<AgentConfig[]>(`/api/agents/topologies/${name}/apply`, { method: 'POST' });

// Providers
export const listProviders = () => json<Record<string, string[]>>('/api/agents/providers');

// Tasks
export const submitTask = (goal: string, completion_criteria: string, agent_config_id?: string) =>
  json<{ task_id: string; status: string }>('/api/tasks', {
    method: 'POST',
    body: JSON.stringify({ goal, completion_criteria, agent_config_id }),
  });
export const listTasks = () => json<Task[]>('/api/tasks');
export const getTask = (id: string) => json<Task>(`/api/tasks/${id}`);
export const stopExecution = () => json<{ ok: boolean }>('/api/tasks/stop', { method: 'POST' });
export const getStats = () => json<Record<string, number>>('/api/tasks/stats');
