export interface AgentConfig {
  id: string;
  name: string;
  provider: string;
  model: string;
  system_prompt: string;
  temperature: number;
  max_tokens: number;
  tool_names: string[];
  can_spawn: boolean;
  position: { x: number; y: number };
}

export interface Task {
  id: string;
  goal: string;
  completion_criteria: string;
  status: 'pending' | 'in_progress' | 'decomposed' | 'completed' | 'failed';
  result: string | null;
  error: string | null;
  parent_task_id: string | null;
  subtask_ids: string[];
  assigned_agent_id: string | null;
  created_at: number;
  completed_at: number | null;
}

export interface ExecutionEvent {
  event: string;
  data: Record<string, unknown>;
  timestamp: number;
}

export const PROVIDER_COLORS: Record<string, string> = {
  anthropic: '#8B5CF6',
  openai: '#10B981',
  openrouter: '#3B82F6',
  local: '#F59E0B',
};

export const PROVIDER_BG: Record<string, string> = {
  anthropic: 'bg-purple-100 border-purple-300',
  openai: 'bg-green-100 border-green-300',
  openrouter: 'bg-blue-100 border-blue-300',
  local: 'bg-amber-100 border-amber-300',
};

export const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-gray-200 text-gray-700',
  in_progress: 'bg-blue-100 text-blue-700',
  decomposed: 'bg-purple-100 text-purple-700',
  completed: 'bg-green-100 text-green-700',
  failed: 'bg-red-100 text-red-700',
};
