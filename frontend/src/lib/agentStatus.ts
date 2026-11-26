import type { Session, Task, Thread, ThreadDelegations } from '../api/client'

/** Badges derived on the client (spec §5). Waiting/approvals = phase B → stay idle. */
export type DerivedAgentStatus =
  | 'running'
  | 'waiting'
  | 'blocked'
  | 'completed'
  | 'idle'

export type StatusCounts = {
  running: number
  waiting: number
  blocked: number
  completed: number
  paused: number
}

export function statusLabel(status: DerivedAgentStatus): string {
  switch (status) {
    case 'running':
      return 'En curso'
    case 'waiting':
      return 'En espera'
    case 'blocked':
      return 'Bloqueado'
    case 'completed':
      return 'Completado'
    default:
      return 'En reposo'
  }
}

export function deriveAgentStatus(opts: {
  agentName: string
  liveStreaming: boolean
  sessions: Session[]
  tasks: Task[]
  /** Phase B: open thread_approval for this specialist. MVP always empty. */
  waitingApproval?: boolean
}): DerivedAgentStatus {
  const { agentName, liveStreaming, sessions, tasks, waitingApproval } = opts

  if (waitingApproval) return 'waiting'

  if (liveStreaming && (agentName === 'orquestador' || agentName === 'fe' || agentName === 'be')) {
    // Stream is global to the active thread; highlight Orquestador while live.
    if (agentName === 'orquestador') return 'running'
  }

  const agentSessions = sessions.filter((s) => s.agent_name === agentName)
  if (agentSessions.some((s) => s.status === 'starting' || s.status === 'running')) {
    return 'running'
  }
  if (agentSessions.some((s) => /fail|error|crashed/i.test(s.status))) {
    return 'blocked'
  }

  const agentTasks = tasks.filter((t) => t.assignee_agent === agentName)
  if (agentTasks.some((t) => t.status === 'doing')) return 'running'
  if (
    agentTasks.length > 0 &&
    agentTasks.every((t) => t.status === 'done') &&
    !agentSessions.some((s) => s.status === 'starting' || s.status === 'running')
  ) {
    // All assigned tasks done and nothing running — still idle unless we want completed.
    // Spec: Completed badge for agent is rare; prefer idle when work finished.
  }

  if (liveStreaming && agentName === 'orquestador') return 'running'

  return 'idle'
}

export function deriveStatusCounts(opts: {
  agentStatuses: Record<string, DerivedAgentStatus>
  threads: Thread[]
  delegations: ThreadDelegations | null
}): StatusCounts {
  const { agentStatuses, threads, delegations } = opts
  const running = Object.values(agentStatuses).filter((s) => s === 'running').length
  const waiting = Object.values(agentStatuses).filter((s) => s === 'waiting').length
  const blocked = Object.values(agentStatuses).filter((s) => s === 'blocked').length

  const closedThreads = threads.filter((t) => t.status === 'closed').length
  const answered =
    delegations?.edges.filter((e) => e.status === 'answered').length ?? 0
  const completed = closedThreads + answered

  return {
    running,
    waiting,
    blocked,
    completed,
    paused: 0, // reserved; no pause API
  }
}
