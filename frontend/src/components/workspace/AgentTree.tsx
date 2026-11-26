import { useRef } from 'react'
import type { Agent, ControlInboxMessage } from '../../api/client'
import type { DerivedAgentStatus } from '../../lib/agentStatus'
import AgentTreeCard, { type AgentKey } from './AgentTreeCard'
import TreeConnectors from './TreeConnectors'

type Props = {
  agentsByName: Record<string, Agent>
  statuses: Record<string, DerivedAgentStatus>
  selected: AgentKey
  onSelect: (key: AgentKey) => void
  onPrompt: (key: AgentKey, text: string) => void | Promise<void>
  promptDisabled?: boolean
  waitingByAgent: Record<string, ControlInboxMessage | undefined>
  decidingId: number | null
  onDecide: (
    inboxId: number,
    approved: boolean,
    note?: string,
  ) => void | Promise<void>
}

export default function AgentTree({
  agentsByName,
  statuses,
  selected,
  onSelect,
  onPrompt,
  promptDisabled,
  waitingByAgent,
  decidingId,
  onDecide,
}: Props) {
  const wrapRef = useRef<HTMLDivElement>(null)
  const orqRef = useRef<HTMLElement>(null)
  const feRef = useRef<HTMLElement>(null)
  const beRef = useRef<HTMLElement>(null)

  const card = (
    key: AgentKey,
    ref: React.RefObject<HTMLElement | null>,
    subAgents: number,
  ) => {
    const pending = waitingByAgent[key] ?? null
    return (
      <AgentTreeCard
        agent={agentsByName[key] ?? null}
        agentKey={key}
        status={statuses[key] ?? 'idle'}
        selected={selected === key}
        subAgents={subAgents}
        cardRef={ref}
        onSelect={() => onSelect(key)}
        onSubmitPrompt={(t) => onPrompt(key, t)}
        disabled={promptDisabled}
        pendingApproval={pending}
        deciding={pending != null && decidingId === pending.id}
        onApprove={
          pending
            ? (note) => onDecide(pending.id, true, note)
            : undefined
        }
        onReject={
          pending
            ? (note) => onDecide(pending.id, false, note)
            : undefined
        }
      />
    )
  }

  return (
    <div className="tree-wrap" ref={wrapRef}>
      <TreeConnectors
        wrapRef={wrapRef}
        orqRef={orqRef}
        feRef={feRef}
        beRef={beRef}
      />
      <div className="ws-tree">
        {card('orquestador', orqRef, 2)}
        <div className="ws-children">
          {card('fe', feRef, 0)}
          {card('be', beRef, 0)}
        </div>
      </div>
      <p className="sr-only">
        Árbol de agentes: Orquestador conectado a FE y a BE.
      </p>
    </div>
  )
}
