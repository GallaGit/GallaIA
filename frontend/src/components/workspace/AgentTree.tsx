import { useRef } from 'react'
import type { Agent } from '../../api/client'
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
}

export default function AgentTree({
  agentsByName,
  statuses,
  selected,
  onSelect,
  onPrompt,
  promptDisabled,
}: Props) {
  const wrapRef = useRef<HTMLDivElement>(null)
  const orqRef = useRef<HTMLElement>(null)
  const feRef = useRef<HTMLElement>(null)
  const beRef = useRef<HTMLElement>(null)

  return (
    <div className="tree-wrap" ref={wrapRef}>
      <TreeConnectors
        wrapRef={wrapRef}
        orqRef={orqRef}
        feRef={feRef}
        beRef={beRef}
      />
      <div className="ws-tree">
        <AgentTreeCard
          agent={agentsByName.orquestador ?? null}
          agentKey="orquestador"
          status={statuses.orquestador ?? 'idle'}
          selected={selected === 'orquestador'}
          subAgents={2}
          cardRef={orqRef}
          onSelect={() => onSelect('orquestador')}
          onSubmitPrompt={(t) => onPrompt('orquestador', t)}
          disabled={promptDisabled}
        />
        <div className="ws-children">
          <AgentTreeCard
            agent={agentsByName.fe ?? null}
            agentKey="fe"
            status={statuses.fe ?? 'idle'}
            selected={selected === 'fe'}
            subAgents={0}
            cardRef={feRef}
            onSelect={() => onSelect('fe')}
            onSubmitPrompt={(t) => onPrompt('fe', t)}
            disabled={promptDisabled}
          />
          <AgentTreeCard
            agent={agentsByName.be ?? null}
            agentKey="be"
            status={statuses.be ?? 'idle'}
            selected={selected === 'be'}
            subAgents={0}
            cardRef={beRef}
            onSelect={() => onSelect('be')}
            onSubmitPrompt={(t) => onPrompt('be', t)}
            disabled={promptDisabled}
          />
        </div>
      </div>
      <p className="sr-only">
        Árbol de agentes: Orquestador conectado a FE y a BE.
      </p>
    </div>
  )
}
