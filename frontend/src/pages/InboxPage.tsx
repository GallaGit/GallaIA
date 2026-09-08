import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, ApiUnavailableError, type InboxItem } from '../api/client'

export default function InboxPage() {
  const [items, setItems] = useState<InboxItem[]>([])
  const [error, setError] = useState<string | null>(null)
  const [apiDown, setApiDown] = useState(false)

  useEffect(() => {
    api
      .inbox()
      .then((data) => {
        setItems(data)
        setApiDown(false)
      })
      .catch((e: Error) => {
        setItems([])
        if (e instanceof ApiUnavailableError) {
          setApiDown(true)
          setError('API no disponible')
        } else {
          setError(e.message)
        }
      })
  }, [])

  return (
    <div>
      <div className="page-header">
        <div>
          <h2>Inbox</h2>
          <p>
            Sesiones en waiting-inbox y tareas en review (GET /inbox).
          </p>
        </div>
      </div>
      {error && <div className="error">{error}</div>}
      <div className="list">
        {items.map((m) => (
          <div key={`${m.kind}-${m.id}`} className="card">
            <div
              style={{
                display: 'flex',
                gap: 8,
                flexWrap: 'wrap',
                marginBottom: 8,
              }}
            >
              <span className="pill">{m.kind}</span>
              <span
                className={
                  m.status === 'waiting-inbox' || m.status === 'review'
                    ? 'pill-coral pill'
                    : 'pill'
                }
              >
                {m.status}
              </span>
              <span className="pill">task {m.task_id}</span>
            </div>
            <strong>{m.title}</strong>
            <p style={{ marginTop: 6 }}>{m.message}</p>
            <p className="muted" style={{ fontSize: '0.8rem' }}>
              {m.created_at}
            </p>
            {m.kind === 'session' && (
              <Link
                to={`/sessions/${encodeURIComponent(m.id)}`}
                className="btn btn-ghost"
                style={{ marginTop: 8, display: 'inline-flex' }}
              >
                Ver sesión
              </Link>
            )}
          </div>
        ))}
        {!items.length && !error && (
          <div className="card empty">
            Inbox vacío — aparece con sesiones waiting-inbox o tareas en review
          </div>
        )}
        {apiDown && !items.length && (
          <div className="card empty">API no disponible</div>
        )}
      </div>
    </div>
  )
}
