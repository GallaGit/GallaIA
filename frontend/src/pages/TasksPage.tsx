import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { Play, Plus } from 'lucide-react'
import {
  api,
  ApiUnavailableError,
  rememberSessionId,
  type Agent,
  type KanbanStatus,
  type Task,
} from '../api/client'

const COLUMNS: KanbanStatus[] = ['todo', 'doing', 'review', 'done']
const LABELS: Record<KanbanStatus, string> = {
  todo: 'Backlog',
  doing: 'Doing',
  review: 'Review',
  done: 'Done',
}

const FALLBACK_AGENTS = [
  { name: 'default', title: 'Default' },
  { name: 'plan', title: 'Plan' },
  { name: 'senior-dev', title: 'Senior Dev' },
]

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [agents, setAgents] = useState<Agent[]>([])
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [assignee, setAssignee] = useState('default')
  const [error, setError] = useState<string | null>(null)
  const [apiDown, setApiDown] = useState(false)
  const [busyId, setBusyId] = useState<string | null>(null)
  const [lastSummary, setLastSummary] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)

  const agentOptions = agents.length ? agents : FALLBACK_AGENTS

  const load = async () => {
    try {
      const [t, a] = await Promise.all([api.tasks(), api.agents()])
      setTasks(t)
      setAgents(a)
      setApiDown(false)
      if (a.length && !a.some((x) => x.name === assignee)) {
        setAssignee(a[0].name)
      }
    } catch (e) {
      setTasks([])
      setAgents([])
      if (e instanceof ApiUnavailableError) {
        setApiDown(true)
        setError('API no disponible')
      } else {
        setError((e as Error).message)
      }
    }
  }

  useEffect(() => {
    void load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const byStatus = useMemo(() => {
    const map: Record<KanbanStatus, Task[]> = {
      todo: [],
      doing: [],
      review: [],
      done: [],
    }
    for (const t of tasks) map[t.status]?.push(t)
    return map
  }, [tasks])

  const onCreate = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    try {
      await api.createTask({
        name,
        description: description || undefined,
        assignee_agent: assignee || 'default',
      })
      setName('')
      setDescription('')
      setShowForm(false)
      await load()
    } catch (err) {
      if (err instanceof ApiUnavailableError) {
        setApiDown(true)
        setError('API no disponible')
      } else {
        setError((err as Error).message)
      }
    }
  }

  const onAssign = async (taskId: string, assignee_agent: string) => {
    setError(null)
    try {
      const updated = await api.patchTask(taskId, { assignee_agent })
      setTasks((prev) => prev.map((t) => (t.id === updated.id ? updated : t)))
    } catch (err) {
      if (err instanceof ApiUnavailableError) {
        setApiDown(true)
        setError('API no disponible')
      } else {
        setError((err as Error).message)
      }
    }
  }

  const onRun = async (task: Task) => {
    setBusyId(task.id)
    setError(null)
    setLastSummary(null)
    try {
      // ONLY POST /tasks/{id}/run — session comes in the response
      const result = await api.runTask(task.id, {
        agent_name: task.assignee_agent || undefined,
      })
      rememberSessionId(result.session.id)
      setLastSummary(result.summary || result.session.summary)
      await load()
    } catch (err) {
      if (err instanceof ApiUnavailableError) {
        setApiDown(true)
        setError('API no disponible')
      } else {
        setError((err as Error).message)
      }
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h2>Tareas</h2>
          <p>Kanban Backlog · Doing · Review · Done. Ejecutar ahora → OpenRouter si hay clave, si no mock.</p>
        </div>
        <button
          className="btn btn-primary"
          type="button"
          disabled={apiDown}
          onClick={() => setShowForm((v) => !v)}
        >
          <Plus size={16} /> Nueva tarea
        </button>
      </div>

      {error && <div className="error">{error}</div>}
      {lastSummary && (
        <div className="card" style={{ marginBottom: '1rem' }}>
          <strong>Última ejecución:</strong> {lastSummary}
        </div>
      )}

      {showForm && (
        <form
          className="card"
          onSubmit={onCreate}
          style={{ marginBottom: '1.25rem' }}
        >
          <div className="grid-2">
            <div className="field">
              <label htmlFor="task-name">Nombre</label>
              <input
                id="task-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                placeholder="p. ej. Escribir plan de feature X"
              />
            </div>
            <div className="field">
              <label htmlFor="task-agent">Agente (assignee_agent)</label>
              <select
                id="task-agent"
                value={assignee}
                onChange={(e) => setAssignee(e.target.value)}
              >
                {agentOptions.map((a) => (
                  <option key={a.name} value={a.name}>
                    {a.title} ({a.name})
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="field">
            <label htmlFor="task-desc">Descripción</label>
            <textarea
              id="task-desc"
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
          <button className="btn btn-coral" type="submit">
            Crear
          </button>
        </form>
      )}

      {apiDown && !tasks.length && (
        <div className="card empty" style={{ marginBottom: '1rem' }}>
          API no disponible — UI vacía hasta que el backend responda en :8000
        </div>
      )}

      <div className="kanban">
        {COLUMNS.map((col) => (
          <div key={col} className="kanban-col">
            <h3>
              <span>{LABELS[col]}</span>
              <span className="pill">{byStatus[col].length}</span>
            </h3>
            {byStatus[col].map((task) => (
              <div key={task.id} className="task-card">
                <h4>{task.name}</h4>
                <p>{task.description || 'Sin descripción'}</p>
                <div className="field" style={{ marginTop: 8, marginBottom: 0 }}>
                  <label htmlFor={`assign-${task.id}`}>Asignar agente</label>
                  <select
                    id={`assign-${task.id}`}
                    value={task.assignee_agent}
                    disabled={apiDown}
                    onChange={(e) => onAssign(task.id, e.target.value)}
                  >
                    {agentOptions.map((a) => (
                      <option key={a.name} value={a.name}>
                        {a.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="task-actions">
                  {col !== 'done' && (
                    <button
                      className="btn btn-primary"
                      type="button"
                      disabled={busyId === task.id || apiDown}
                      onClick={() => onRun(task)}
                    >
                      <Play size={14} />
                      {busyId === task.id ? 'Ejecutando…' : 'Ejecutar ahora'}
                    </button>
                  )}
                </div>
              </div>
            ))}
            {!byStatus[col].length && <div className="empty">Vacío</div>}
          </div>
        ))}
      </div>
    </div>
  )
}
