import { useState } from 'react'
import type { Agent } from '../../api/client'
import {
  statusLabel,
  type DerivedAgentStatus,
} from '../../lib/agentStatus'

export type AgentKey = 'orquestador' | 'fe' | 'be'

type Props = {
  agent: Agent | null
  agentKey: AgentKey
  status: DerivedAgentStatus
  selected: boolean
  subAgents: number
  cardRef: React.RefObject<HTMLElement | null>
  onSelect: () => void
  onSubmitPrompt: (text: string) => void | Promise<void>
  disabled?: boolean
}

const PLACEHOLDERS: Record<AgentKey, string> = {
  orquestador: 'Escribe un prompt para el Orquestador…',
  fe: 'Instrucción para FE…',
  be: 'Instrucción para BE…',
}

export default function AgentTreeCard({
  agent,
  agentKey,
  status,
  selected,
  subAgents,
  cardRef,
  onSelect,
  onSubmitPrompt,
  disabled,
}: Props) {
  const [draft, setDraft] = useState('')
  const title =
    agent?.title ??
    (agentKey === 'orquestador'
      ? 'Orquestador'
      : agentKey === 'fe'
        ? 'FE'
        : 'BE')
  const role =
    agent?.one_job ??
    (agentKey === 'orquestador'
      ? 'Hablar con Ociel, planificar, delegar a FE/BE'
      : agentKey === 'fe'
        ? 'React / TypeScript / UI'
        : 'FastAPI / API / datos')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (!draft.trim() || disabled) return
    const text = draft.trim()
    setDraft('')
    await onSubmitPrompt(text)
  }

  return (
    <article
      ref={cardRef as React.RefObject<HTMLElement>}
      className={`ws-agent ws-agent--${agentKey}${selected ? ' is-selected' : ''}`}
      data-agent={agentKey}
      tabIndex={0}
      role="button"
      aria-pressed={selected}
      aria-label={`${title}, ${statusLabel(status)}`}
      onClick={onSelect}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onSelect()
        }
      }}
    >
      <div className="ws-agent-top">
        <div>
          <h3>{title}</h3>
          <p className="ws-agent-role">{role}</p>
        </div>
        <span className={`ws-badge ws-badge--${status}`}>
          {status !== 'idle' && status !== 'completed' && (
            <span className="ws-pulse" aria-hidden="true" />
          )}
          {statusLabel(status)}
        </span>
      </div>
      <div className="ws-agent-meta">
        <span>Sub-agentes: {subAgents}</span>
        <span title="Sin API de worktrees en el MVP">
          Worktree: — <em className="ws-prox">(placeholder)</em>
        </span>
      </div>
      <form className="ws-prompt-row" onSubmit={(e) => void handleSubmit(e)}>
        <label className="sr-only" htmlFor={`prompt-${agentKey}`}>
          {PLACEHOLDERS[agentKey]}
        </label>
        <input
          id={`prompt-${agentKey}`}
          type="text"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onClick={(e) => e.stopPropagation()}
          placeholder={PLACEHOLDERS[agentKey]}
          disabled={disabled}
          maxLength={20000}
        />
        <button
          type="submit"
          className={`ws-btn${agentKey === 'orquestador' ? ' ws-btn-primary' : ''}`}
          disabled={disabled || !draft.trim()}
          onClick={(e) => e.stopPropagation()}
        >
          Enviar
        </button>
      </form>
      {agentKey !== 'orquestador' && (
        <p className="ws-hint">
          El mensaje se envía al Orquestador indicando destino {agentKey.toUpperCase()}.
        </p>
      )}
    </article>
  )
}
