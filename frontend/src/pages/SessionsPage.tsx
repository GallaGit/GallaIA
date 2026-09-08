import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import {
  api,
  ApiUnavailableError,
  rememberSessionId,
  type Session,
} from '../api/client'

export default function SessionsPage() {
  const { id } = useParams()
  const [sessions, setSessions] = useState<Session[]>([])
  const [selected, setSelected] = useState<Session | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [apiDown, setApiDown] = useState(false)

  useEffect(() => {
    setError(null)
    setApiDown(false)

    const load = async () => {
      try {
        if (id) {
          const s = await api.session(id)
          setSelected(s)
          rememberSessionId(s.id)
          return
        }
        setSelected(null)
        const list = await api.sessions()
        setSessions(Array.isArray(list) ? list : [])
        for (const s of list ?? []) rememberSessionId(s.id)
      } catch (e) {
        setSelected(null)
        setSessions([])
        if (e instanceof ApiUnavailableError) {
          setApiDown(true)
          setError('API no disponible')
        } else {
          setError((e as Error).message)
        }
      }
    }
    void load()
  }, [id])

  if (selected) {
    return (
      <div>
        <div className="page-header">
          <div>
            <Link
              to="/sessions"
              className="muted"
              style={{ display: 'inline-flex', gap: 6, alignItems: 'center' }}
            >
              <ArrowLeft size={16} /> Volver
            </Link>
            <h2 style={{ marginTop: '0.5rem' }}>Sesión {selected.id}</h2>
            <p>
              <span className="pill">{selected.status}</span>{' '}
              <span className="pill">runner: {selected.runner}</span>{' '}
              <span className="pill">{selected.agent_name}</span>{' '}
              <span className="pill">task {selected.task_id}</span>
            </p>
          </div>
        </div>
        {selected.summary && (
          <div className="card" style={{ marginBottom: '1rem' }}>
            <h3>Resumen</h3>
            <p className="mono">{selected.summary}</p>
          </div>
        )}
        <div className="card">
          <h3>Tool events</h3>
          <div className="tool-log">
            {(selected.tool_events ?? []).map((ev, i) => (
              <div key={`${ev.at}-${i}`} className="tool-row">
                <span className="muted mono">{ev.at}</span>
                <span className="pill">{ev.name}</span>
                <span className="mono" style={{ fontSize: '0.8rem' }}>
                  {JSON.stringify(ev.output)}
                </span>
              </div>
            ))}
            {!selected.tool_events?.length && (
              <div className="empty">Sin eventos</div>
            )}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h2>Sesiones</h2>
          <p>Listado GET /sessions · detalle GET /sessions/:id</p>
        </div>
      </div>
      {error && <div className="error">{error}</div>}
      <div className="list">
        {sessions.map((s) => (
          <Link
            key={s.id}
            to={`/sessions/${encodeURIComponent(s.id)}`}
            className="card"
            style={{ display: 'block' }}
          >
            <strong>{s.id}</strong>
            <div className="muted">
              {s.status} · {s.runner} · {s.agent_name} · task {s.task_id} ·{' '}
              {s.started_at}
            </div>
            {s.summary && <div style={{ marginTop: 6 }}>{s.summary}</div>}
          </Link>
        ))}
        {!sessions.length && !error && (
          <div className="card empty">
            Aún no hay sesiones — ejecuta una tarea desde Tasks (Run now)
          </div>
        )}
        {apiDown && !sessions.length && (
          <div className="card empty">API no disponible</div>
        )}
      </div>
    </div>
  )
}
