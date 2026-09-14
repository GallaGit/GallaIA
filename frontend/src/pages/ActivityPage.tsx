import { useEffect, useState } from 'react'
import { api, ApiUnavailableError, type ActivityEvent } from '../api/client'

export default function ActivityPage() {
  const [events, setEvents] = useState<ActivityEvent[]>([])
  const [error, setError] = useState<string | null>(null)
  const [apiDown, setApiDown] = useState(false)

  useEffect(() => {
    api
      .activity(50)
      .then((data) => {
        setEvents(data)
        setApiDown(false)
        setError(null)
      })
      .catch((e: Error) => {
        setEvents([])
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
          <h2>Activity</h2>
          <p>Feed reciente (GET /api/v1/activity) — SSE live viewer después</p>
        </div>
      </div>
      {error && <div className="error">{error}</div>}
      {apiDown && <div className="card empty">API no disponible</div>}
      {!apiDown && !error && events.length === 0 && (
        <div className="card empty">Sin eventos todavía</div>
      )}
      {events.length > 0 && (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
            {events.map((ev) => (
              <li
                key={ev.id}
                style={{
                  padding: '0.85rem 1.1rem',
                  borderBottom: '1px solid var(--border, #e8e2d9)',
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    gap: '0.5rem',
                    alignItems: 'center',
                    flexWrap: 'wrap',
                  }}
                >
                  <span className="pill pill-amber">{ev.type}</span>
                  <span className="mono" style={{ fontSize: '0.75rem' }}>
                    #{ev.id}
                  </span>
                  <span className="muted" style={{ fontSize: '0.75rem', marginLeft: 'auto' }}>
                    {ev.created_at}
                  </span>
                </div>
                <p style={{ margin: '0.35rem 0 0' }}>{ev.message}</p>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
