import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  api,
  ApiUnavailableError,
  type Thread,
  type ThreadDetail,
  type ThreadMessage,
} from '../api/client'

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
    if (!id) {
      setDetail(null)
      return
    }
    void loadDetail(id)
  }, [id, loadDetail])

  // F1.4 live stream: replay + advance_thread output appended as it arrives.
  // Only opened on explicit user action (Avanzar / send), never on select.
  // Closed when switching threads or leaving the page.
  useEffect(() => {
    if (!id || streamFor !== String(id) || streamKey === 0) return
    addedRef.current = 0
    setLive(true)
    const es = new EventSource(api.threadStreamUrl(id, 6))

    es.addEventListener('message', (ev) => {
      try {
        const msg = JSON.parse((ev as MessageEvent).data) as ThreadMessage
        setDetail((prev) => {
          if (!prev || String(prev.id) !== String(id)) return prev
          const { merged, added } = mergeMessages(prev.messages, [msg])
          if (added > 0) addedRef.current += added
          return added > 0 ? { ...prev, messages: merged } : prev
        })
      } catch {
        /* ignore malformed frames */
      }
    })
    es.addEventListener('end', (ev) => {
      try {
        const data = JSON.parse((ev as MessageEvent).data) as {
          created?: number
        }
        const n =
          typeof data.created === 'number' ? data.created : addedRef.current
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
      es.close()
    })
    es.addEventListener('error', (ev) => {
      const data = (ev as MessageEvent).data as string | null
      if (data) {
        try {
          const body = JSON.parse(data) as { message?: string }
          setDetailError(body.message ?? data)
        } catch {
          setDetailError(data)
        }
        setLive(false)
        es.close()
      }
    })
    es.onerror = () => {
      // Transport-level failure (no frame data): close so the browser does
      // not auto-reconnect (each reconnect would re-run agent steps). The
      // snapshot loaded via GET remains visible.
      es.close()
      setLive(false)
      setStreamError('Se perdió la conexión en directo. Pulsa Avanzar para reintentar.')
    }

    return () => {
      es.close()
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
      setStreamError(null)
      setStreamFor(String(id))
      setStreamKey((k) => k + 1)
    } catch (e) {
      setDetailError(errorMessage(e))
    } finally {
      setBusy(false)
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
