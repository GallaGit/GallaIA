import { useEffect, useMemo, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'

type Frame = { event: string; data: string; at: string }

function apiRoot(): string {
  return `${(import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '')}/api/v1`
}

export default function LivePage() {
  const { id: routeId } = useParams()
  const [params, setParams] = useSearchParams()
  const [sessionIdInput, setSessionIdInput] = useState(
    routeId ?? params.get('session') ?? '',
  )
  const [activeId, setActiveId] = useState<string | null>(routeId ?? params.get('session'))
  const [frames, setFrames] = useState<Frame[]>([])
  const [status, setStatus] = useState<string>('idle')
  const [error, setError] = useState<string | null>(null)

  const streamUrl = useMemo(() => {
    if (!activeId) return null
    const q = new URLSearchParams({ heartbeat_seconds: '10' })
    return `${apiRoot()}/sessions/${encodeURIComponent(activeId)}/stream?${q}`
  }, [activeId])

  useEffect(() => {
    if (!streamUrl || !activeId) return
    setFrames([])
    setError(null)
    setStatus('connecting')
    const es = new EventSource(streamUrl)

    const push = (event: string, data: string) => {
      setFrames((prev) => [
        ...prev.slice(-199),
        { event, data, at: new Date().toISOString() },
      ])
    }

    es.addEventListener('status', (ev) => {
      setStatus('live')
      push('status', (ev as MessageEvent).data)
      try {
        const j = JSON.parse((ev as MessageEvent).data) as { status?: string }
        if (j.status) setStatus(`live:${j.status}`)
      } catch {
        /* ignore */
      }
    })
    es.addEventListener('tool', (ev) => push('tool', (ev as MessageEvent).data))
    es.addEventListener('heartbeat', (ev) => push('heartbeat', (ev as MessageEvent).data))
    es.addEventListener('error', (ev) => {
      const data = (ev as MessageEvent).data
      if (data) {
        push('error', data)
        setError(data)
      }
    })
    es.addEventListener('end', (ev) => {
      push('end', (ev as MessageEvent).data)
      setStatus('ended')
      es.close()
    })
    es.onerror = () => {
      setStatus((s) => (s.startsWith('live') ? s : 'error'))
    }

    return () => es.close()
  }, [streamUrl, activeId])

  const connect = () => {
    const id = sessionIdInput.trim()
    if (!id) return
    setActiveId(id)
    setParams({ session: id })
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <Link
            to="/sessions"
            className="muted"
            style={{ display: 'inline-flex', gap: 6, alignItems: 'center' }}
          >
            <ArrowLeft size={16} /> Sesiones
          </Link>
          <h2 style={{ marginTop: '0.5rem' }}>Live viewer</h2>
          <p>
            SSE <span className="mono">GET /api/v1/sessions/&#123;id&#125;/stream</span> — status +
            tool log
          </p>
        </div>
      </div>

      <div className="card" style={{ marginBottom: '1rem' }}>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
          <label className="muted" htmlFor="live-session-id">
            Session id
          </label>
          <input
            id="live-session-id"
            className="mono"
            value={sessionIdInput}
            onChange={(e) => setSessionIdInput(e.target.value)}
            placeholder="e.g. 12"
            style={{ minWidth: 120 }}
          />
          <button type="button" className="btn" onClick={connect}>
            Conectar
          </button>
          <span className="pill">{status}</span>
        </div>
        {error && <div className="error" style={{ marginTop: '0.75rem' }}>{error}</div>}
      </div>

      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <ul style={{ listStyle: 'none', margin: 0, padding: 0, maxHeight: '70vh', overflow: 'auto' }}>
          {frames.length === 0 && (
            <li className="empty" style={{ padding: '1rem' }}>
              Sin frames todavía — elige una sesión y conecta.
            </li>
          )}
          {frames.map((f, i) => (
            <li
              key={`${f.at}-${i}`}
              style={{
                padding: '0.65rem 1rem',
                borderBottom: '1px solid var(--border, #e8e2d9)',
              }}
            >
              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                <span className="pill pill-amber">{f.event}</span>
                <span className="muted" style={{ fontSize: '0.75rem', marginLeft: 'auto' }}>
                  {f.at}
                </span>
              </div>
              <pre className="mono" style={{ margin: '0.35rem 0 0', fontSize: '0.75rem', whiteSpace: 'pre-wrap' }}>
                {f.data}
              </pre>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
