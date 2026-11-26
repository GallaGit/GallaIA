import type { Session, Task, Thread, ThreadDelegations } from '../api/client'

/** Badges derived on the client (spec §5). */
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
  /** Open thread_approval targeting this specialist (or Orquestador notice). */
  waitingApproval?: boolean
}): DerivedAgentStatus {
  const { agentName, liveStreaming, sessions, tasks, waitingApproval } = opts

  if (waitingApproval) return 'waiting'

  if (liveStreaming && agentName === 'orquestador') return 'running'

  const agentSessions = sessions.filter((s) => s.agent_name === agentName)
  if (agentSessions.some((s) => s.status === 'starting' || s.status === 'running')) {
    return 'running'
  }
  if (agentSessions.some((s) => /fail|error|crashed/i.test(s.status))) {
    return 'blocked'
  }

  const agentTasks = tasks.filter((t) => t.assignee_agent === agentName)
  if (agentTasks.some((t) => t.status === 'doing')) return 'running'

  return 'idle'
}

export function deriveStatusCounts(opts: {
  agentStatuses: Record<string, DerivedAgentStatus>
  threads: Thread[]
  delegations: ThreadDelegations | null
  /** Open F2.2c approvals (preferred for Waiting count). */
  openApprovals?: number
}): StatusCounts {
  const { agentStatuses, threads, delegations, openApprovals } = opts
  const running = Object.values(agentStatuses).filter((s) => s === 'running').length
  const waitingFromAgents = Object.values(agentStatuses).filter(
    (s) => s === 'waiting',
  ).length
  const waiting =
    typeof openApprovals === 'number' ? openApprovals : waitingFromAgents
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
