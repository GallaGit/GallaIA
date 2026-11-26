import { useState } from 'react'
import type { Agent, ControlInboxMessage } from '../../api/client'
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
  pendingApproval?: ControlInboxMessage | null
  deciding?: boolean
  onApprove?: (note: string) => void | Promise<void>
  onReject?: (note: string) => void | Promise<void>
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
  pendingApproval,
  deciding,
  onApprove,
  onReject,
}: Props) {
  const [draft, setDraft] = useState('')
  const [note, setNote] = useState('')
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
      className={`ws-agent ws-agent--${agentKey}${selected ? ' is-selected' : ''}${
        pendingApproval ? ' is-waiting' : ''
      }`}
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

      {pendingApproval && (
        <div
          className="ws-approval"
          onClick={(e) => e.stopPropagation()}
          onKeyDown={(e) => e.stopPropagation()}
        >
          <h4>Aprobación pendiente</h4>
          <p>{pendingApproval.body}</p>
          <label className="sr-only" htmlFor={`note-${agentKey}`}>
            Nota opcional
          </label>
          <input
            id={`note-${agentKey}`}
            type="text"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Nota de contexto (opcional)…"
            disabled={deciding}
          />
          <div className="ws-approval-row">
            <button
              type="button"
              className="ws-btn ws-btn-ok"
              disabled={deciding || !onApprove}
              onClick={() => void onApprove?.(note)}
            >
              {deciding ? '…' : 'Aprobar'}
            </button>
            <button
              type="button"
              className="ws-btn ws-btn-danger"
              disabled={deciding || !onReject}
              onClick={() => void onReject?.(note)}
            >
              {deciding ? '…' : 'Rechazar'}
            </button>
          </div>
        </div>
      )}

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
          El mensaje se envía al Orquestador indicando destino{' '}
          {agentKey.toUpperCase()}.
        </p>
      )}
    </article>
  )
}
