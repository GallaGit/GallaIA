import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, ApiUnavailableError, type InboxItem } from '../api/client'

type LocalInboxItem = InboxItem & {
  unread: boolean
  snoozed: boolean
}

function kindChipClass(kind: string, status: string): string {
  if (kind === 'session' || status === 'waiting-inbox' || status === 'failed') {
    return 'pill-coral pill'
  }
  if (status === 'review') return 'pill-amber pill'
  return 'pill'
}

function kindLabel(kind: string): string {
  if (kind === 'session') return 'alert'
  if (kind === 'task') return 'handoff'
  return kind
}

export default function InboxPage() {
  const [items, setItems] = useState<LocalInboxItem[]>([])
  const [selectedKey, setSelectedKey] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [apiDown, setApiDown] = useState(false)

  useEffect(() => {
    api
      .inbox()
      .then((data) => {
        const mapped = data.map((m) => ({
          ...m,
          unread: true,
          snoozed: false,
        }))
        setItems(mapped)
        setSelectedKey(mapped[0] ? `${mapped[0].kind}-${mapped[0].id}` : null)
        setApiDown(false)
      })
      .catch((e: Error) => {
        setItems([])
        setSelectedKey(null)
        if (e instanceof ApiUnavailableError) {
          setApiDown(true)
          setError('API no disponible')
        } else {
          setError(e.message)
        }
      })
  }, [])

  const visible = useMemo(
    () => items.filter((m) => !m.snoozed),
    [items],
  )

  const selected = useMemo(
    () => visible.find((m) => `${m.kind}-${m.id}` === selectedKey) ?? null,
    [visible, selectedKey],
  )

  const keyOf = (m: InboxItem) => `${m.kind}-${m.id}`

  const acknowledge = (key: string) => {
    setItems((prev) =>
      prev.map((m) =>
        keyOf(m) === key ? { ...m, unread: false } : m,
      ),
    )
  }

  const snooze = (key: string) => {
    setItems((prev) =>
      prev.map((m) =>
        keyOf(m) === key ? { ...m, snoozed: true, unread: false } : m,
      ),
    )
    setSelectedKey((cur) => {
      if (cur !== key) return cur
      const next = visible.find((m) => keyOf(m) !== key)
      return next ? keyOf(next) : null
    })
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h2>Inbox</h2>
          <p>Handoffs · alerts · atención humana (GET /inbox)</p>
        </div>
        <button
          type="button"
          className="btn btn-ghost"
          disabled={!visible.some((m) => m.unread)}
          onClick={() =>
            setItems((prev) => prev.map((m) => ({ ...m, unread: false })))
          }
        >
          Mark all read
        </button>
      </div>
      {error && <div className="error">{error}</div>}

      {visible.length > 0 ? (
        <div className="inbox-layout">
          <div className="inbox-list">
            {visible.map((m) => {
              const key = keyOf(m)
              return (
                <button
                  key={key}
                  type="button"
                  className={`inbox-item${m.unread ? ' unread' : ''}${
                    selectedKey === key ? ' active' : ''
                  }`}
                  onClick={() => {
                    setSelectedKey(key)
                  }}
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
            {selected ? (
              <>
                <h2>{selected.title}</h2>
                <p className="mono">
                  {selected.id} · task {selected.task_id} · {selected.status}
                </p>
                <p style={{ marginTop: 12 }}>{selected.message}</p>
                <p className="muted" style={{ fontSize: '0.8rem' }}>
                  {selected.created_at}
                </p>
                <div className="actions">
                  {selected.kind === 'session' ? (
                    <Link
                      to={`/sessions/${encodeURIComponent(selected.id)}`}
                      className="btn btn-primary"
                    >
                      Open session
                    </Link>
                  ) : (
                    <Link to="/tasks" className="btn btn-primary">
                      Open task
                    </Link>
                  )}
                  <button
                    type="button"
                    className="btn"
                    onClick={() => acknowledge(keyOf(selected))}
                  >
                    Acknowledge
                  </button>
                  <button
                    type="button"
                    className="btn"
                    onClick={() => snooze(keyOf(selected))}
                  >
                    Snooze
                  </button>
                </div>
              </>
            ) : (
              <div className="empty">Selecciona un ítem</div>
            )}
          </article>
        </div>
      ) : (
        <>
          {!error && (
            <div className="card empty">
              Inbox vacío — aparece con sesiones waiting-inbox o tareas en review
            </div>
          )}
          {apiDown && (
            <div className="card empty">API no disponible</div>
          )}
        </>
      )}
    </div>
  )
}
