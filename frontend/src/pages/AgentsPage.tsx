import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { api, ApiUnavailableError, type Agent } from '../api/client'

type AgentStatus = 'healthy' | 'degraded' | 'offline'
type StatusFilter = 'all' | AgentStatus

type AgentWithStatus = Agent & {
  status: AgentStatus
  last_activity?: string | null
}

function resolveStatus(agent: Agent): AgentStatus {
  const raw = (agent as Agent & { status?: string }).status
  if (raw === 'healthy' || raw === 'degraded' || raw === 'offline') return raw
  return 'healthy'
}

function resolveLastActivity(agent: Agent): string | null {
  const a = agent as Agent & {
    last_activity?: string
    last_active?: string
    updated_at?: string
  }
  return a.last_activity ?? a.last_active ?? a.updated_at ?? null
}

function StatusChip({ status }: { status: AgentStatus }) {
  return <span className={`status-chip ${status}`}>{status}</span>
}

function AgentCard({ agent }: { agent: AgentWithStatus }) {
  const initial = (agent.title || agent.name || '?').charAt(0).toUpperCase()
  return (
    <Link
      to={`/agents/${encodeURIComponent(agent.name)}`}
      className="card agent-card"
    >
      <div className="agent-top">
        <div className="agent-avatar">{initial}</div>
        <div>
          <h3>{agent.title}</h3>
          <div className="role">{agent.one_job || agent.model}</div>
        </div>
      </div>
      <StatusChip status={agent.status} />
      <div className="agent-meta">
        <span>
          {agent.last_activity
            ? `Last active ${agent.last_activity}`
            : 'Seed · sin heartbeat'}
        </span>
        <span className="mono">{agent.name}</span>
      </div>
    </Link>
  )
}

export default function AgentsPage() {
  const { name } = useParams()
  const [agents, setAgents] = useState<AgentWithStatus[]>([])
  const [selected, setSelected] = useState<Agent | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [apiDown, setApiDown] = useState(false)
  const [filter, setFilter] = useState<StatusFilter>('all')
  const [ctaNote, setCtaNote] = useState(false)

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
          setAgents(
            data.map((a) => ({
              ...a,
              status: resolveStatus(a),
              last_activity: resolveLastActivity(a),
            })),
          )
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

  const counts = useMemo(() => {
    const c = { all: agents.length, healthy: 0, degraded: 0, offline: 0 }
    for (const a of agents) c[a.status] += 1
    return c
  }, [agents])

  const filtered = useMemo(() => {
    if (filter === 'all') return agents
    return agents.filter((a) => a.status === filter)
  }, [agents, filter])

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
              <span className="pill mono">{selected.name}</span>{' '}
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
          <p>Fleet del control plane · seeds GET /agents</p>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 6 }}>
          <button
            type="button"
            className="btn btn-primary btn-muted"
            title="POST /agents no está en el contrato Fase 1"
            onClick={() => setCtaNote(true)}
          >
            Registrar agente
          </button>
          {ctaNote && (
            <span className="muted" style={{ fontSize: '0.78rem' }}>
              Próximamente — seeds son GET-only
            </span>
          )}
        </div>
      </div>
      {error && <div className="error">{error}</div>}

      <div className="filter-pills">
        {(
          [
            ['all', 'All'],
            ['healthy', 'Healthy'],
            ['degraded', 'Degraded'],
            ['offline', 'Offline'],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            type="button"
            className={`filter-pill${filter === key ? ' active' : ''}`}
            onClick={() => setFilter(key)}
          >
            {label} · {counts[key]}
          </button>
        ))}
      </div>

      <div className="agents-grid">
        {filtered.map((agent) => (
          <AgentCard key={agent.name} agent={agent} />
        ))}
      </div>

      {!agents.length && !error && (
        <div className="card empty" style={{ marginTop: '1rem' }}>
          Aún no hay agentes
        </div>
      )}
      {!agents.length && apiDown && (
        <div className="card empty" style={{ marginTop: '1rem' }}>
          API no disponible
        </div>
      )}
      {agents.length > 0 && !filtered.length && (
        <div className="card empty" style={{ marginTop: '1rem' }}>
          Ningún agente con estado «{filter}»
        </div>
      )}
    </div>
  )
}
