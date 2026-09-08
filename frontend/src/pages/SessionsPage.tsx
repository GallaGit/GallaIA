import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { api, type Session } from '../api/client'

export default function SessionsPage() {
  const { id } = useParams()
  const [sessions, setSessions] = useState<Session[]>([])
  const [selected, setSelected] = useState<Session | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .sessions()
      .then((data) => {
        setSessions(data)
        if (id) setSelected(data.find((s) => String(s.id) === id) ?? null)
        else setSelected(null)
      })
      .catch((e: Error) => setError(e.message))
  }, [id])

  if (selected) {
    return (
      <div>
        <div className="page-header">
          <div>
            <Link to="/sessions" className="muted" style={{ display: 'inline-flex', gap: 6, alignItems: 'center' }}>
              <ArrowLeft size={16} /> Volver
            </Link>
            <h2 style={{ marginTop: '0.5rem' }}>Sesión #{selected.id}</h2>
            <p>
              <span className="pill">{selected.status}</span>{' '}
              <span className="pill">runner: {selected.runner}</span>{' '}
              <span className="pill">agent #{selected.agent_id}</span>
              {selected.task_id != null && <span className="pill"> task #{selected.task_id}</span>}
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
          <h3>Tool-call log</h3>
          <div className="tool-log">
            {(selected.tool_call_log ?? []).map((ev, i) => (
              <div key={`${ev.ts}-${i}`} className="tool-row">
                <span className="muted mono">{ev.ts}</span>
                <span className="pill">{ev.tool}</span>
                <span>{ev.detail}</span>
              </div>
            ))}
            {!selected.tool_call_log?.length && <div className="empty">Sin eventos</div>}
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
          <p>Historial de ejecuciones (mock / Claude stub) con log de herramientas.</p>
        </div>
      </div>
      {error && <div className="error">{error}</div>}
      <div className="list">
        {sessions.map((s) => (
          <Link key={s.id} to={`/sessions/${s.id}`} className="card" style={{ display: 'block' }}>
            <strong>Sesión #{s.id}</strong>
            <div className="muted">
              {s.status} · {s.runner} · agent #{s.agent_id}
              {s.task_id != null ? ` · task #${s.task_id}` : ''} · {s.started_at}
            </div>
          </Link>
        ))}
        {!sessions.length && !error && <div className="card empty">Aún no hay sesiones — ejecuta una tarea</div>}
      </div>
    </div>
  )
}
