import { useEffect, useRef, useState } from 'react'
import type { Agent, Thread, ThreadDetail, ThreadMessage } from '../../api/client'
import type { AgentKey } from './AgentTreeCard'
import { statusLabel, type DerivedAgentStatus } from '../../lib/agentStatus'
import { MAX_MESSAGE_CHARS } from '../../hooks/useActiveThread'

type Props = {
  selectedKey: AgentKey
  agent: Agent | null
  statuses: Record<string, DerivedAgentStatus>
  threads: Thread[]
  activeThreadId: string | null
  detail: ThreadDetail | null
  live: boolean
  busy: boolean
  closed: boolean
  autoAdvance: boolean
  advanceInfo: string | null
  detailError: string | null
  streamError: string | null
  onSelectThread: (id: string | null) => void
  onSend: (text: string) => void | Promise<void>
  onAdvance: () => void
  onCloseThread: () => void
  onAutoAdvance: (v: boolean) => void
  onCreateThread: () => void
}

function kindLabel(kind: string): string {
  if (kind === 'delegation') return 'delegación'
  if (kind === 'result') return 'resultado'
  return 'mensaje'
}

function isHighlighted(m: ThreadMessage, agentKey: AgentKey): boolean {
  return m.sender === agentKey || m.recipient === agentKey
}

export default function AgentInspector({
  selectedKey,
  agent,
  statuses,
  threads,
  activeThreadId,
  detail,
  live,
  busy,
  closed,
  autoAdvance,
  advanceInfo,
  detailError,
  streamError,
  onSelectThread,
  onSend,
  onAdvance,
  onCloseThread,
  onAutoAdvance,
  onCreateThread,
}: Props) {
  const [tab, setTab] = useState<'chat' | 'context' | 'settings'>('chat')
  const [draft, setDraft] = useState('')
  const chatRef = useRef<HTMLDivElement>(null)
  const title =
    agent?.title ??
    (selectedKey === 'orquestador'
      ? 'Orquestador'
      : selectedKey.toUpperCase())

  useEffect(() => {
    const el = chatRef.current
    if (!el) return
    el.scrollTop = el.scrollHeight
  }, [detail?.messages.length, live])

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!draft.trim() || busy || closed) return
    const text = draft.trim()
    setDraft('')
    await onSend(text)
  }

  return (
    <aside className="ws-inspector" aria-label="Panel del agente">
      <div className="ws-insp-head">
        <div className="ws-insp-who">{title}</div>
        <div className="ws-insp-sub">
          {agent?.one_job ?? 'Inspector del agente · hilo activo'}
        </div>
      </div>

      <div className="ws-tabs" role="tablist" aria-label="Pestañas del inspector">
        {(
          [
            ['chat', 'Chat', false],
            ['context', 'Contexto', false],
            ['worktree', 'Worktree', true],
            ['files', 'Archivos', true],
            ['tests', 'Tests', true],
            ['settings', 'Ajustes', false],
          ] as const
        ).map(([id, label, soon]) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={!soon && tab === id}
            className={!soon && tab === id ? 'on' : undefined}
            disabled={soon}
            onClick={() => {
              if (id === 'chat' || id === 'context' || id === 'settings') {
                setTab(id)
              }
            }}
          >
            {label}
            {soon && <span className="ws-prox">Próx.</span>}
          </button>
        ))}
      </div>

      {tab === 'chat' && (
        <>
          <div className="ws-thread-bar">
            <label className="sr-only" htmlFor="ws-thread-select">
              Hilo activo
            </label>
            <select
              id="ws-thread-select"
              value={activeThreadId ?? ''}
              onChange={(e) =>
                onSelectThread(e.target.value ? e.target.value : null)
              }
            >
              <option value="">Sin hilo seleccionado</option>
              {threads.map((t) => (
                <option key={t.id} value={String(t.id)}>
                  {t.status === 'open' ? '●' : '○'} {t.title}
                </option>
              ))}
            </select>
            <button
              type="button"
              className="ws-btn"
              onClick={onCreateThread}
              disabled={busy}
            >
              Crear hilo
            </button>
          </div>

          {(detailError || streamError) && (
            <div className="ws-error" role="alert">
              {detailError || streamError}
            </div>
          )}
          {advanceInfo && <p className="ws-muted-line">{advanceInfo}</p>}

          <div className="ws-chat" ref={chatRef} role="log" aria-live="polite">
            {!activeThreadId && (
              <div className="ws-empty">
                Elige o crea un hilo para chatear con el Orquestador.
              </div>
            )}
            {activeThreadId && detail && !detail.messages.length && (
              <div className="ws-empty">Sin mensajes todavía</div>
            )}
            {detail?.messages.map((m) => (
              <div
                key={m.id}
                className={`ws-msg ${m.sender === 'user' ? 'user' : 'agent'}${
                  isHighlighted(m, selectedKey) ? ' is-hl' : ''
                }`}
              >
                <small>
                  {m.sender} → {m.recipient ?? '—'} · {kindLabel(m.kind)}
                </small>
                <span style={{ whiteSpace: 'pre-wrap' }}>{m.body}</span>
              </div>
            ))}
            {live && (
              <div className="ws-stream" aria-label="Transmitiendo en directo">
                <div className="ws-dots" aria-hidden="true">
                  <i />
                  <i />
                  <i />
                </div>
                <div>
                  <small>Orquestador · en directo</small>
                  <div>Recibiendo respuestas…</div>
                </div>
              </div>
            )}
          </div>

          <div className="ws-composer">
            <div className="ws-subs">
              Sub-agentes:{' '}
              <span data-status={statuses.fe}>
                FE · {statusLabel(statuses.fe ?? 'idle')}
              </span>
              {' · '}
              <span data-status={statuses.be}>
                BE · {statusLabel(statuses.be ?? 'idle')}
              </span>
            </div>
            <label
              htmlFor="ws-auto-advance"
              className="ws-check"
            >
              <input
                id="ws-auto-advance"
                type="checkbox"
                checked={autoAdvance}
                onChange={(e) => onAutoAdvance(e.target.checked)}
              />
              Avanzar automáticamente al enviar
            </label>
            <form className="ws-composer-row" onSubmit={(e) => void handleSend(e)}>
              <label className="sr-only" htmlFor="ws-chat-draft">
                Mensaje al Orquestador
              </label>
              <input
                id="ws-chat-draft"
                type="text"
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                placeholder="Escribe al Orquestador…"
                disabled={busy || closed || !activeThreadId}
                maxLength={MAX_MESSAGE_CHARS}
              />
              <button
                type="button"
                className="ws-btn"
                onClick={onAdvance}
                disabled={busy || live || closed || !activeThreadId}
              >
                Avanzar
              </button>
              <button
                type="submit"
                className="ws-btn ws-btn-primary"
                disabled={busy || closed || !activeThreadId || !draft.trim()}
              >
                Enviar
              </button>
              <button
                type="button"
                className="ws-btn"
                onClick={onCloseThread}
                disabled={busy || closed || !activeThreadId}
              >
                Cerrar hilo
              </button>
            </form>
            {closed && (
              <p className="ws-hint">Este hilo está cerrado.</p>
            )}
          </div>
        </>
      )}

      {tab === 'context' && (
        <div className="ws-tab-body">
          {agent ? (
            <>
              <p>
                <strong>one_job:</strong> {agent.one_job}
              </p>
              <p>
                <strong>model:</strong> <span className="mono">{agent.model}</span>
              </p>
              <p>
                <strong>runner:</strong> {agent.runner_preference}
              </p>
              <p className="ws-muted-line">{agent.prompt_origin}</p>
              {agent.skills?.length > 0 && (
                <p>
                  Skills:{' '}
                  {agent.skills.map((s) => (
                    <span key={s} className="ws-pill">
                      {s}
                    </span>
                  ))}
                </p>
              )}
            </>
          ) : (
            <div className="ws-empty">Agente no cargado</div>
          )}
        </div>
      )}

      {tab === 'settings' && (
        <div className="ws-tab-body">
          <p className="ws-muted-line">
            Placeholder · fase posterior: tema, token de operador (sin
            re-mostrarlo) y ruta del runner en solo lectura.
          </p>
          <p>
            Nombre seed: <span className="mono">{selectedKey}</span>
          </p>
        </div>
      )}
    </aside>
  )
}
