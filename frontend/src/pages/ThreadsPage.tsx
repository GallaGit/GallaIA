import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api, ApiUnavailableError, type Thread, type ThreadDetail } from '../api/client'

function kindLabel(kind: string): string {
  if (kind === 'delegation') return 'delegación'
  if (kind === 'result') return 'resultado'
  return 'mensaje'
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
    if (!id) {
      setDetail(null)
      return
    }
    void loadDetail(id)
  }, [id, loadDetail])

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
      await api.postThreadMessage(id, draft.trim())
      setDraft('')
      await loadDetail(id)
    } catch (e) {
      setDetailError(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  const handleAdvance = async () => {
    if (!id || busy || detail?.status === 'closed') return
    setBusy(true)
    setDetailError(null)
    try {
      const res = await api.advanceThread(id, 6)
      const n = res.created?.length ?? 0
      setAdvanceInfo(
        n === 0
          ? 'Sin respuestas pendientes'
          : n === 1
            ? '1 respuesta nueva'
            : `${n} respuestas nuevas`,
      )
      await loadDetail(id)
    } catch (e) {
      setDetailError(errorMessage(e))
    } finally {
      setBusy(false)
    }
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
                        t.status === 'open' ? 'pill-green pill' : 'pill'
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
                    detail.status === 'open' ? 'pill-green pill' : 'pill'
                  }
                >
                  {detail.status}
                </span>
              </p>
              {detailError && <div className="error">{detailError}</div>}
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
                  onClick={() => void handleAdvance()}
                  disabled={busy || closed}
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
