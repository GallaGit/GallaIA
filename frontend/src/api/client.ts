/** AgentOS API client — canonical base /api/v1/agentos (see CONTRACT.md) */

const BASE = `${(import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '')}/api/v1/agentos`

export type KanbanStatus = 'todo' | 'doing' | 'review' | 'done'
export type RunnerKind = 'mock' | 'anthropic'

export type Agent = {
  name: string
  title: string
  model: string
  one_job: string
  skills: string[]
  mcp: string[]
  runner_preference: string
  prompt_origin: string
  foundational_prompt: string
  role_prompt: string
}

export type Task = {
  id: string
  name: string
  description: string
  assignee_agent: string
  status: KanbanStatus
  activity: string[]
  created_at: string
  updated_at: string
}

export type ToolEvent = {
  name: string
  input: Record<string, unknown>
  output: Record<string, unknown>
  at: string
}

export type Session = {
  id: string
  task_id: string
  agent_name: string
  runner: RunnerKind
  status: string
  summary: string
  tool_events: ToolEvent[]
  started_at: string
  ended_at: string | null
}

export type RunResponse = {
  runner: RunnerKind
  used_anthropic: boolean
  summary: string
  task: Task
  session: Session
}

export type InboxItem = {
  id: string
  kind: 'session' | 'task'
  task_id: string
  title: string
  status: string
  message: string
  created_at: string
}

export class ApiUnavailableError extends Error {
  constructor(message = 'API no disponible') {
    super(message)
    this.name = 'ApiUnavailableError'
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${BASE}${path}`, {
      headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
      ...init,
    })
  } catch {
    throw new ApiUnavailableError()
  }

  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = body?.error?.message ?? body?.detail ?? detail
    } catch {
      /* ignore */
    }
    throw new Error(detail || `HTTP ${res.status}`)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

const SESSION_IDS_KEY = 'gallaia.sessionIds'

export function rememberSessionId(id: string): void {
  try {
    const raw = localStorage.getItem(SESSION_IDS_KEY)
    const ids: string[] = raw ? (JSON.parse(raw) as string[]) : []
    if (!ids.includes(id)) {
      ids.unshift(id)
      localStorage.setItem(SESSION_IDS_KEY, JSON.stringify(ids.slice(0, 50)))
    }
  } catch {
    /* ignore */
  }
}

export function rememberedSessionIds(): string[] {
  try {
    const raw = localStorage.getItem(SESSION_IDS_KEY)
    return raw ? (JSON.parse(raw) as string[]) : []
  } catch {
    return []
  }
}

export const api = {
  agents: () => request<Agent[]>('/agents'),
  agent: (name: string) =>
    request<Agent>(`/agents/${encodeURIComponent(name)}`),
  tasks: () => request<Task[]>('/tasks'),
  task: (id: string) => request<Task>(`/tasks/${encodeURIComponent(id)}`),
  createTask: (body: {
    name: string
    description?: string
    assignee_agent?: string
  }) =>
    request<Task>('/tasks', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  /** assignee_agent = seed NAME (default|plan|senior-dev), not numeric id */
  patchTask: (
    id: string,
    body: { assignee_agent?: string; status?: KanbanStatus },
  ) =>
    request<Task>(`/tasks/${encodeURIComponent(id)}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),
  /** Run now — do NOT create a session first; session is in the response */
  runTask: (
    id: string,
    body: { agent_name?: string; runner?: RunnerKind } = { runner: 'mock' },
  ) =>
    request<RunResponse>(`/tasks/${encodeURIComponent(id)}/run`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  sessions: () => request<Session[]>('/sessions'),
  session: (id: string) =>
    request<Session>(`/sessions/${encodeURIComponent(id)}`),
  inbox: () => request<InboxItem[]>('/inbox'),
}
