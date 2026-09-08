import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Bot, ArrowLeft } from 'lucide-react'
import { api, ApiUnavailableError, type Agent } from '../api/client'

export default function AgentsPage() {
  const { name } = useParams()
  const [agents, setAgents] = useState<Agent[]>([])
  const [selected, setSelected] = useState<Agent | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [apiDown, setApiDown] = useState(false)

  useEffect(() => {
    setError(null)
    setApiDown(false)
    const load = async () => {
      try {
        if (name) {
          const agent = await api.agent(name)
          setSelected(agent)
          setAgents([])
        } else {
          const data = await api.agents()
          setAgents(data)
          setSelected(null)
        }
      } catch (e) {
        setSelected(null)
        setAgents([])
        if (e instanceof ApiUnavailableError) {
          setApiDown(true)
          setError('API no disponible')
        } else {
          setError((e as Error).message)
        }
      }
    }
    void load()
  }, [name])

  if (selected) {
    return (
      <div>
        <div className="page-header">
          <div>
            <Link
              to="/agents"
              className="muted"
              style={{ display: 'inline-flex', gap: 6, alignItems: 'center' }}
            >
              <ArrowLeft size={16} /> Volver
            </Link>
            <h2 style={{ marginTop: '0.5rem' }}>{selected.title}</h2>
            <p>
              <span className="pill">{selected.name}</span>{' '}
              <span className="pill">{selected.model}</span>{' '}
              <span className="pill-coral pill">
                runner: {selected.runner_preference}
              </span>
            </p>
          </div>
        </div>
        <div className="card" style={{ marginBottom: '1rem' }}>
          <p className="muted" style={{ marginTop: 0 }}>
            {selected.one_job}
          </p>
          <p className="muted" style={{ fontSize: '0.85rem' }}>
            {selected.prompt_origin}
          </p>
          {selected.skills?.length > 0 && (
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 8 }}>
              {selected.skills.map((s) => (
                <span key={s} className="pill">
                  {s}
                </span>
              ))}
            </div>
          )}
        </div>
        <div className="grid-2">
          <div className="card">
            <h3>Foundational prompt</h3>
            <div className="prompt-box mono">{selected.foundational_prompt}</div>
          </div>
          <div className="card">
            <h3>Role prompt</h3>
            <div className="prompt-box mono">{selected.role_prompt}</div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h2>Agentes</h2>
          <p>Catálogo seed: default · plan · senior-dev</p>
        </div>
      </div>
      {error && <div className="error">{error}</div>}
      <div className="list">
        {agents.map((agent) => (
          <Link
            key={agent.name}
            to={`/agents/${encodeURIComponent(agent.name)}`}
            className="card"
            style={{ display: 'block' }}
          >
            <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
              <Bot size={20} color="var(--indigo)" />
              <div>
                <strong>{agent.title}</strong>
                <div className="muted">
                  {agent.name} · {agent.model} · {agent.runner_preference}
                </div>
                <div className="muted" style={{ marginTop: 4 }}>
                  {agent.one_job}
                </div>
              </div>
            </div>
          </Link>
        ))}
        {!agents.length && !error && (
          <div className="card empty">Sin agentes</div>
        )}
        {!agents.length && apiDown && (
          <div className="card empty">API no disponible</div>
        )}
      </div>
    </div>
  )
}
