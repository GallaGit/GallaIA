import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  api,
  ApiUnavailableError,
  type ControlInboxMessage,
  type InboxItem,
} from '../api/client'
import { useControlInbox } from '../hooks/useControlInbox'

type LocalHandoff = InboxItem & {
  unread: boolean
  snoozed: boolean
}

function kindChipClass(kind: string, status: string): string {
  if (kind === 'thread_approval') return 'pill-amber pill'
  if (kind === 'session' || status === 'waiting-inbox' || status === 'failed') {
    return 'pill-coral pill'
  }
  if (status === 'review') return 'pill-amber pill'
  return 'pill'
}

function kindLabel(kind: string): string {
  if (kind === 'thread_approval') return 'aprobación'
  if (kind === 'session') return 'alert'
  if (kind === 'task') return 'handoff'
  return kind
}

export default function InboxPage() {
  const control = useControlInbox(true)
  const [handoffs, setHandoffs] = useState<LocalHandoff[]>([])
  const [selectedKey, setSelectedKey] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [apiDown, setApiDown] = useState(false)
  const [note, setNote] = useState('')
  const [loadingHandoffs, setLoadingHandoffs] = useState(false)

  const loadHandoffs = useCallback(async () => {
    setLoadingHandoffs(true)
    try {
      const data = await api.inbox()
      setHandoffs(
        data.map((m) => ({
          ...m,
          unread: true,
          snoozed: false,
        })),
      )
      setApiDown(false)
      setError(null)
    } catch (e) {
      setHandoffs([])
      if (e instanceof ApiUnavailableError) {
        setApiDown(true)
        setError('API no disponible')
      } else {
        setError((e as Error).message)
      }
    } finally {
      setLoadingHandoffs(false)
    }
  }, [])

  useEffect(() => {
    void loadHandoffs()
  }, [loadHandoffs])

  // Prefer first open approval, else first handoff.
  useEffect(() => {
    if (selectedKey) return
    if (control.approvals[0]) {
      setSelectedKey(`approval-${control.approvals[0].id}`)
      return
    }
    const first = handoffs.find((m) => !m.snoozed)
    if (first) setSelectedKey(`handoff-${first.kind}-${first.id}`)
  }, [control.approvals, handoffs, selectedKey])

  const visibleHandoffs = useMemo(
    () => handoffs.filter((m) => !m.snoozed),
    [handoffs],
  )

  const selectedApproval: ControlInboxMessage | null = useMemo(() => {
    if (!selectedKey?.startsWith('approval-')) return null
    const id = Number(selectedKey.slice('approval-'.length))
    return control.approvals.find((a) => a.id === id) ?? null
  }, [selectedKey, control.approvals])

  const selectedHandoff = useMemo(() => {
    if (!selectedKey?.startsWith('handoff-')) return null
    const rest = selectedKey.slice('handoff-'.length)
    return visibleHandoffs.find((m) => `${m.kind}-${m.id}` === rest) ?? null
  }, [selectedKey, visibleHandoffs])

  const handleDecide = async (approved: boolean) => {
    if (!selectedApproval) return
    try {
      await control.decide(selectedApproval.id, approved, note)
      setNote('')
      setSelectedKey(null)
    } catch {
      /* shown via control.error */
    }
  }

  const loading = control.loading || loadingHandoffs
  const combinedError = error || control.error

  return (
    <div>
      <div className="page-header">
        <div>
          <h2>Inbox</h2>
          <p>
            Primero aprobaciones F2.2c (GET /api/v1/inbox) · luego handoffs
            AgentOS
            {control.live ? ' · SSE en vivo' : ''}
          </p>
        </div>
        <button
          type="button"
          className="btn btn-ghost"
          onClick={() => {
            void control.reload()
            void loadHandoffs()
          }}
          disabled={loading}
        >
          {loading ? 'Cargando…' : 'Actualizar'}
        </button>
      </div>
      {combinedError && (
        <div className="error" role="alert">
          {combinedError}
        </div>
      )}

      {control.approvals.length === 0 &&
      visibleHandoffs.length === 0 &&
      !loading ? (
        <>
          {!combinedError && (
            <div className="card empty">
              Inbox vacío — sin aprobaciones abiertas ni handoffs AgentOS
            </div>
          )}
          {apiDown && <div className="card empty">API no disponible</div>}
        </>
      ) : (
        <div className="inbox-layout">
          <div className="inbox-list">
            {control.approvals.length > 0 && (
              <div
                className="muted"
                style={{ padding: '0.55rem 0.9rem', fontSize: '0.75rem' }}
              >
                Aprobaciones de hilo (F2.2c)
              </div>
            )}
            {control.approvals.map((a) => {
              const key = `approval-${a.id}`
              return (
                <button
                  key={key}
                  type="button"
                  className={`inbox-item unread${
                    selectedKey === key ? ' active' : ''
                  }`}
                  onClick={() => setSelectedKey(key)}
                >
                  <div className="bar" />
                  <div className="body">
                    <h4>
                      <span className={kindChipClass(a.kind, a.status)}>
                        {kindLabel(a.kind)}
                      </span>
                      {a.target_agent
                        ? `Delegación a ${a.target_agent.toUpperCase()}`
                        : `Inbox #${a.id}`}
                    </h4>
                    <p>{a.body}</p>
                    <div className="when">{a.created_at}</div>
                  </div>
                </button>
              )
            })}

            {visibleHandoffs.length > 0 && (
              <div
                className="muted"
                style={{ padding: '0.55rem 0.9rem', fontSize: '0.75rem' }}
              >
                Handoffs AgentOS
              </div>
            )}
            {visibleHandoffs.map((m) => {
              const key = `handoff-${m.kind}-${m.id}`
              return (
                <button
                  key={key}
                  type="button"
                  className={`inbox-item${m.unread ? ' unread' : ''}${
                    selectedKey === key ? ' active' : ''
                  }`}
                  onClick={() => setSelectedKey(key)}
                >
                  <div className="bar" />
                  <div className="body">
                    <h4>
                      <span className={kindChipClass(m.kind, m.status)}>
                        {kindLabel(m.kind)}
                      </span>
                      {m.title}
                    </h4>
                    <p>{m.message}</p>
                    <div className="when">{m.created_at}</div>
                  </div>
                </button>
              )
            })}
          </div>

          <article className="card inbox-detail">
            {selectedApproval ? (
              <>
                <h2>
                  Aprobación #{selectedApproval.id}
                  {selectedApproval.target_agent
                    ? ` · ${selectedApproval.target_agent.toUpperCase()}`
                    : ''}
                </h2>
                <p className="mono">
                  thread {selectedApproval.thread_id ?? '—'} ·{' '}
                  {selectedApproval.status}
                </p>
                <p style={{ marginTop: 12 }}>{selectedApproval.body}</p>
                <div className="field" style={{ marginTop: '0.75rem' }}>
                  <label htmlFor="inbox-decide-note">Nota (opcional)</label>
                  <input
                    id="inbox-decide-note"
                    type="text"
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    disabled={control.decidingId === selectedApproval.id}
                  />
                </div>
                <div className="actions">
                  <button
                    type="button"
                    className="btn btn-primary"
                    disabled={control.decidingId === selectedApproval.id}
                    onClick={() => void handleDecide(true)}
                  >
                    Aprobar
                  </button>
                  <button
                    type="button"
                    className="btn btn-coral"
                    disabled={control.decidingId === selectedApproval.id}
                    onClick={() => void handleDecide(false)}
                  >
                    Rechazar
                  </button>
                  {selectedApproval.thread_id != null && (
                    <Link
                      to={`/threads/${encodeURIComponent(
                        String(selectedApproval.thread_id),
                      )}`}
                      className="btn"
                    >
                      Abrir hilo
                    </Link>
                  )}
                </div>
              </>
            ) : selectedHandoff ? (
              <>
                <h2>{selectedHandoff.title}</h2>
                <p className="mono">
                  {selectedHandoff.id} · task {selectedHandoff.task_id} ·{' '}
                  {selectedHandoff.status}
                </p>
                <p style={{ marginTop: 12 }}>{selectedHandoff.message}</p>
                <p className="muted" style={{ fontSize: '0.8rem' }}>
                  {selectedHandoff.created_at}
                </p>
                <div className="actions">
                  {selectedHandoff.kind === 'session' ? (
                    <Link
                      to={`/sessions/${encodeURIComponent(selectedHandoff.id)}`}
                      className="btn btn-primary"
                    >
                      Open session
                    </Link>
                  ) : (
                    <Link to="/tasks" className="btn btn-primary">
                      Open task
                    </Link>
                  )}
                </div>
              </>
            ) : (
              <div className="empty">
                {loading ? 'Cargando…' : 'Selecciona un ítem'}
              </div>
            )}
          </article>
        </div>
      )}
    </div>
  )
}
