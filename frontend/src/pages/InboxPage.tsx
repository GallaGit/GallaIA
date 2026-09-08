import { useEffect, useState, type FormEvent } from 'react'
import { api, type InboxMessage } from '../api/client'

export default function InboxPage() {
  const [messages, setMessages] = useState<InboxMessage[]>([])
  const [replies, setReplies] = useState<Record<number, string>>({})
  const [error, setError] = useState<string | null>(null)

  const load = () =>
    api
      .inbox()
      .then(setMessages)
      .catch((e: Error) => setError(e.message))

  useEffect(() => {
    load()
  }, [])

  const onReply = async (e: FormEvent, id: number) => {
    e.preventDefault()
    const body = replies[id]?.trim()
    if (!body) return
    setError(null)
    try {
      await api.replyInbox(id, body)
      setReplies((r) => ({ ...r, [id]: '' }))
      await load()
    } catch (err) {
      setError((err as Error).message)
    }
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h2>Inbox</h2>
          <p>Canal de interrupción humana. Reply es stub en Phase 1 (no reanuda contenedor real).</p>
        </div>
      </div>
      {error && <div className="error">{error}</div>}
      <div className="list">
        {messages.map((m) => (
          <div key={m.id} className="card">
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 8 }}>
              <span className="pill">{m.from_role}</span>
              <span className={m.status === 'open' ? 'pill-coral pill' : 'pill-green pill'}>{m.status}</span>
              {m.task_id != null && <span className="pill">task #{m.task_id}</span>}
            </div>
            <p style={{ marginTop: 0 }}>{m.body}</p>
            {m.reply_body && (
              <p className="muted">
                <strong>Respuesta:</strong> {m.reply_body}
              </p>
            )}
            {m.status === 'open' && (
              <form onSubmit={(e) => onReply(e, m.id)} style={{ marginTop: 12 }}>
                <div className="field">
                  <label htmlFor={`reply-${m.id}`}>Responder</label>
                  <textarea
                    id={`reply-${m.id}`}
                    rows={2}
                    value={replies[m.id] ?? ''}
                    onChange={(e) => setReplies((r) => ({ ...r, [m.id]: e.target.value }))}
                  />
                </div>
                <button className="btn btn-primary" type="submit">
                  Enviar respuesta
                </button>
              </form>
            )}
          </div>
        ))}
        {!messages.length && !error && (
          <div className="card empty">Inbox vacío — aparece cuando un agent usa approval gate</div>
        )}
      </div>
    </div>
  )
}
