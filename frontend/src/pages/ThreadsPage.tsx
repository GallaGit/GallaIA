import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  api,
  ApiUnavailableError,
  type Thread,
  type ThreadDelegations,
  type ThreadDetail,
  type ThreadMessage,
} from '../api/client'
import { openEventStream } from '../api/sse'

function kindLabel(kind: string): string {
  if (kind === 'delegation') return 'delegación'
  if (kind === 'result') return 'resultado'
  return 'mensaje'
}

/** Append incoming messages without duplicates, ordered by id. */
function mergeMessages(
  prev: ThreadMessage[],
  incoming: ThreadMessage[],
): { merged: ThreadMessage[]; added: number } {
  const ids = new Set(prev.map((m) => m.id))
  const fresh = incoming.filter((m) => !ids.has(m.id))
  if (!fresh.length) return { merged: prev, added: 0 }
  return {
    merged: [...prev, ...fresh].sort((a, b) => a.id - b.id),
    added: fresh.length,
  }
}

const AUTO_ADVANCE_KEY = 'gallaia.autoAdvance'

function loadAutoAdvance(): boolean {
  try {
    const raw = localStorage.getItem(AUTO_ADVANCE_KEY)
    return raw === null ? true : raw !== 'false'
  } catch {
    return true
  }
}
function errorMessage(e: unknown): string {
  if (e instanceof ApiUnavailableError) return 'API no disponible'
  return (e as Error).message
}

export default function ThreadsPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [threads, setThreads] = useState<Thread[]>([])
  const [detail, setDetail] = useState<ThreadDetail | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [detailError, setDetailError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [newTitle, setNewTitle] = useState('')
  const [draft, setDraft] = useState('')
  const [advanceInfo, setAdvanceInfo] = useState<string | null>(null)
  const [streamKey, setStreamKey] = useState(0)
  const [live, setLive] = useState(false)
  // Thread the user explicitly asked to stream (Avanzar / send). Selecting a
  // thread never opens the stream: opening it runs advance_thread.
  const [streamFor, setStreamFor] = useState<string | null>(null)
  const [streamError, setStreamError] = useState<string | null>(null)
  const [delegations, setDelegations] = useState<ThreadDelegations | null>(null)
  const [autoAdvance, setAutoAdvance] = useState<boolean>(loadAutoAdvance)
  const addedRef = useRef(0)

  const loadThreads = useCallback(async () => {
    try {
      const list = await api.threads()
      setThreads(Array.isArray(list) ? list : [])
    } catch (e) {
      setThreads([])
      setError(errorMessage(e))
    }
  }, [])

  const loadDetail = useCallback(async (threadId: string) => {
    setDetailError(null)
    try {
      const d = await api.thread(threadId)
      setDetail(d)
    } catch (e) {
      setDetail(null)
      setDetailError(errorMessage(e))
    }
  }, [])

  const loadDelegations = useCallback(async (threadId: string) => {
    try {
      const d = await api.getThreadDelegations(threadId)
      setDelegations(d)
    } catch {
      setDelegations(null)
    }
  }, [])

  useEffect(() => {
    setError(null)
    void loadThreads()
  }, [loadThreads])

  useEffect(() => {
    setDraft('')
    setAdvanceInfo(null)
    setDetailError(null)
    setStreamError(null)
    setStreamFor(null)
    setDelegations(null)
    if (!id) {
      setDetail(null)
      return
    }
    void loadDetail(id)
    void loadDelegations(id)
  }, [id, loadDetail, loadDelegations])

  // Refetch delegations when the live stream ends.
  useEffect(() => {
    if (!live && id) void loadDelegations(id)
  }, [live, id, loadDelegations])

  // F1.4 live stream: replay + advance_thread output appended as it arrives.
  // Only opened on explicit user action (Avanzar / send), never on select.
  // Closed when switching threads or leaving the page.
  useEffect(() => {
    if (!id || streamFor !== String(id) || streamKey === 0) return
    addedRef.current = 0
    setLive(true)
    // Fetch-based SSE (not EventSource) so the operator token travels in the
    // Authorization header, never in the URL. No auto-reconnect.
    const close = openEventStream(
      api.threadStreamUrl(id, 6),
      {
        message: (data) => {
          try {
            const msg = JSON.parse(data) as ThreadMessage
            setDetail((prev) => {
              if (!prev || String(prev.id) !== String(id)) return prev
              const { merged, added } = mergeMessages(prev.messages, [msg])
              if (added > 0) addedRef.current += added
              return added > 0 ? { ...prev, messages: merged } : prev
            })
          } catch {
            /* ignore malformed frames */
          }
        },
        end: (data) => {
          try {
            const parsed = JSON.parse(data) as { created?: number }
            const n =
              typeof parsed.created === 'number' ? parsed.created : addedRef.current
            setAdvanceInfo(
              n === 0
                ? 'Sin respuestas pendientes'
                : n === 1
                  ? '1 respuesta nueva'
                  : `${n} respuestas nuevas`,
            )
          } catch {
            setAdvanceInfo(null)
          }
          setLive(false)
          close()
        },
        error: (data) => {
          if (data) {
            try {
              const body = JSON.parse(data) as { message?: string }
              setDetailError(body.message ?? data)
            } catch {
              setDetailError(data)
            }
            setLive(false)
            close()
          }
        },
      },
      () => {
        // Transport-level or HTTP failure: the GET snapshot remains visible.
        close()
        setLive(false)
        setStreamError('Se perdió la conexión en directo. Pulsa Avanzar para reintentar.')
      },
    )

    return () => {
      close()
      setLive(false)
    }
  }, [id, streamKey, streamFor])

  const handleCreate = async () => {
    if (!newTitle.trim() || busy) return
    setBusy(true)
    setError(null)
    try {
      const t = await api.createThread(newTitle.trim())
      setNewTitle('')
      await loadThreads()
      navigate(`/threads/${encodeURIComponent(String(t.id))}`)
    } catch (e) {
      setError(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  const handleSend = async () => {
    if (!id || !draft.trim() || busy || detail?.status === 'closed') return
    setBusy(true)
    setAdvanceInfo(null)
    setDetailError(null)
    try {
      const msg = await api.postThreadMessage(id, draft.trim())
      setDraft('')
      setDetail((prev) =>
        prev && String(prev.id) === String(id)
          ? { ...prev, messages: mergeMessages(prev.messages, [msg]).merged }
          : prev,
      )
      // Open the stream so the agents' replies arrive live.
      if (autoAdvance) {
        setStreamError(null)
        setStreamFor(String(id))
        setStreamKey((k) => k + 1)
      } else {
        void loadDelegations(id)
      }
    } catch (e) {
      setDetailError(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  const handleAutoAdvance = (checked: boolean) => {
    setAutoAdvance(checked)
    try {
      localStorage.setItem(AUTO_ADVANCE_KEY, String(checked))
    } catch {
      /* ignore */
    }
  }

  const handleAdvance = () => {
    if (!id || busy || live || detail?.status === 'closed') return
    setDetailError(null)
    setAdvanceInfo('Transmitiendo en directo…')
    // Reopen the stream: the backend replays + runs advance_thread (mock LLM)
    // and pushes each new message without reloading.
    setStreamError(null)
    setStreamFor(String(id))
    setStreamKey((k) => k + 1)
  }

  const handleClose = async () => {
    if (!id || busy || detail?.status === 'closed') return
    setBusy(true)
    setAdvanceInfo(null)
    setDetailError(null)
    try {
      await api.closeThread(id)
      await loadThreads()
      await loadDetail(id)
      await loadDelegations(id)
      // Drop any live stream so it cannot report the (now expected) closed
      // state as an error.
      setStreamFor(null)
    } catch (e) {
      setDetailError(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  const closed = detail?.status === 'closed'

  return (
    <div>
      <div className="page-header">
        <div>
          <h2>Conversaciones</h2>
          <p>Hilos con el Orquestador · GET /threads</p>
        </div>
      </div>
      {error && <div className="error">{error}</div>}

      <div className="inbox-layout">
        <div>
          <form
            className="card"
            style={{ marginBottom: '0.9rem' }}
            onSubmit={(e) => {
              e.preventDefault()
              void handleCreate()
            }}
          >
            <h3 style={{ margin: '0 0 0.5rem' }}>Nuevo hilo</h3>
            <div className="field">
              <label htmlFor="thread-title">Título</label>
              <input
                id="thread-title"
                type="text"
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                placeholder="Título del hilo"
                disabled={busy}
              />
            </div>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={busy || !newTitle.trim()}
            >
              Crear hilo
            </button>
          </form>

          <div className="inbox-list">
            {threads.map((t) => (
              <button
                key={t.id}
                type="button"
                className={`inbox-item${id === String(t.id) ? ' active' : ''}`}
                onClick={() =>
                  navigate(`/threads/${encodeURIComponent(String(t.id))}`)
                }
              >
                <div className="bar" />
                <div className="body">
                  <h4>
                    <span
                      className={
                        t.status === 'open' ? 'pill pill-green' : 'pill'
                      }
                    >
                      {t.status}
                    </span>
                    {t.title}
                  </h4>
                  <div className="when">{t.created_at}</div>
                </div>
              </button>
            ))}
            {!threads.length && !error && (
              <div className="empty">Aún no hay hilos</div>
            )}
          </div>
        </div>

        <article className="card inbox-detail">
          {!id ? (
            <div className="empty">Selecciona un hilo</div>
          ) : detail ? (
            <>
              <h2>{detail.title}</h2>
              <p className="mono">
                {detail.id} · {detail.status} · {detail.created_at}
              </p>
              <p>
                <span
                  className={
                    detail.status === 'open' ? 'pill pill-green' : 'pill'
                  }
                >
                  {detail.status}
                </span>{' '}
                {live && (
                  <span className="pill pill-green">en directo</span>
                )}
              </p>
              {detailError && <div className="error">{detailError}</div>}
              {streamError && (
                <div className="error" role="alert">
                  {streamError}
                </div>
              )}
              {advanceInfo && (
                <p className="muted" style={{ fontSize: '0.85rem' }}>
                  {advanceInfo}
                </p>
              )}
              <div className="tool-log" style={{ marginTop: '1rem' }}>
                {detail.messages.map((m) => (
                  <div key={m.id} className="tool-row">
                    <span className="muted mono">
                      {m.sender} → {m.recipient ?? '—'}
                    </span>
                    <span className="pill">{kindLabel(m.kind)}</span>
                    <span>
                      <span style={{ whiteSpace: 'pre-wrap' }}>{m.body}</span>
                      <span
                        className="muted mono"
                        style={{ display: 'block', marginTop: 4 }}
                      >
                        {m.created_at}
                      </span>
                    </span>
                  </div>
                ))}
                {!detail.messages.length && (
                  <div className="empty">Sin mensajes todavía</div>
                )}
              </div>
              <div className="field" style={{ marginTop: '1rem' }}>
                <label htmlFor="thread-draft">Mensaje</label>
                <textarea
                  id="thread-draft"
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  placeholder="Escribe un mensaje…"
                  rows={3}
                  disabled={busy || closed}
                />
              </div>
              <div className="field">
                <label
                  htmlFor="auto-advance"
                  style={{ display: 'flex', gap: '0.4rem', alignItems: 'center' }}
                >
                  <input
                    id="auto-advance"
                    type="checkbox"
                    checked={autoAdvance}
                    onChange={(e) => handleAutoAdvance(e.target.checked)}
                  />
                  Avanzar automáticamente al enviar
                </label>
              </div>
              <div>
                <h3>Delegaciones</h3>
                {!delegations || !delegations.edges.length ? (
                  <div className="empty">Sin delegaciones todavía</div>
                ) : (
                  <div className="tool-log">
                    {delegations.edges.map((e) => (
                      <div key={e.delegation_id} className="tool-row">
                        <span className="muted mono">
                          Orquestador → {e.target.toUpperCase()}
                        </span>
                        <span
                          className={
                            e.status === 'answered' ? 'pill pill-green' : 'pill pill-amber'
                          }
                        >
                          {e.status === 'answered'
                            ? 'respondida'
                            : 'pendiente'}
                        </span>
                        <span title={e.brief}>
                          {e.brief.length > 80
                            ? `${e.brief.slice(0, 80)}…`
                            : e.brief}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
                {delegations && delegations.summary_id != null && (
                  <p className="muted" style={{ fontSize: '0.85rem' }}>
                    Resumen enviado al usuario
                  </p>
                )}
              </div>
              <div className="actions">
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => void handleSend()}
                  disabled={busy || closed || !draft.trim()}
                >
                  Enviar al Orquestador
                </button>
                <button
                  type="button"
                  className="btn"
                  onClick={() => handleAdvance()}
                  disabled={busy || live || closed}
                >
                  Avanzar
                </button>
                <button
                  type="button"
                  className="btn"
                  onClick={() => void handleClose()}
                  disabled={busy || closed}
                >
                  Cerrar hilo
                </button>
              </div>
            </>
          ) : (
            <>
              {detailError && <div className="error">{detailError}</div>}
              {!detailError && <div className="empty">Selecciona un hilo</div>}
            </>
          )}
        </article>
      </div>
    </div>
  )
}
