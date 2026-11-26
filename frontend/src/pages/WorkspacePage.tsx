import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  api,
  ApiUnavailableError,
  type Agent,
  type Project,
  type Session,
  type Task,
} from '../api/client'
import AgentTree from '../components/workspace/AgentTree'
import AgentInspector from '../components/workspace/AgentInspector'
import DependenciesPanel from '../components/workspace/DependenciesPanel'
import QuickActions from '../components/workspace/QuickActions'
import type { AgentKey } from '../components/workspace/AgentTreeCard'
import { useActiveThread } from '../hooks/useActiveThread'
import {
  deriveAgentStatus,
  deriveStatusCounts,
  type DerivedAgentStatus,
} from '../lib/agentStatus'
import AgentsPage from './AgentsPage'

const AGENT_ORDER: AgentKey[] = ['orquestador', 'fe', 'be']

type PendingSend = { key: AgentKey; text: string; id: string }

export default function WorkspacePage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const view = searchParams.get('view') === 'list' ? 'list' : 'tree'

  const [agents, setAgents] = useState<Agent[]>([])
  const [sessions, setSessions] = useState<Session[]>([])
  const [tasks, setTasks] = useState<Task[]>([])
  const [project, setProject] = useState<Project | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [selected, setSelected] = useState<AgentKey>('orquestador')
  const [openTabs, setOpenTabs] = useState<AgentKey[]>(['orquestador'])
  const [threadId, setThreadId] = useState<string | null>(null)
  const pendingSend = useRef<PendingSend | null>(null)

  const chat = useActiveThread(threadId)

  const agentsByName = useMemo(() => {
    const map: Record<string, Agent> = {}
    for (const a of agents) map[a.name] = a
    return map
  }, [agents])

  const loadFleet = useCallback(async () => {
    try {
      const [agentList, sessionList, taskList, projects] = await Promise.all([
        api.agents(),
        api.sessions().catch(() => [] as Session[]),
        api.tasks().catch(() => [] as Task[]),
        api.projects().catch(() => [] as Project[]),
      ])
      setAgents(Array.isArray(agentList) ? agentList : [])
      setSessions(Array.isArray(sessionList) ? sessionList : [])
      setTasks(Array.isArray(taskList) ? taskList : [])
      const preferred =
        projects.find((p) => p.slug === 'default') ?? projects[0] ?? null
      setProject(preferred)
      setLoadError(null)
    } catch (e) {
      setAgents([])
      if (e instanceof ApiUnavailableError) {
        setLoadError('API no disponible')
      } else {
        setLoadError((e as Error).message)
      }
    }
  }, [])

  useEffect(() => {
    void loadFleet()
  }, [loadFleet])

  useEffect(() => {
    if (threadId) return
    const open = chat.threads.find((t) => t.status === 'open')
    if (open) setThreadId(String(open.id))
  }, [chat.threads, threadId])

  // Flush prompt queued while creating / switching thread.
  useEffect(() => {
    const pending = pendingSend.current
    if (!pending || threadId !== pending.id) return
    if (!chat.detail || String(chat.detail.id) !== pending.id) return
    if (chat.detail.status === 'closed') return
    pendingSend.current = null
    void chat.sendMessage(pending.text, pending.key)
  }, [threadId, chat.detail, chat])

  const statuses = useMemo(() => {
    const map: Record<string, DerivedAgentStatus> = {}
    for (const key of AGENT_ORDER) {
      map[key] = deriveAgentStatus({
        agentName: key,
        liveStreaming: chat.live,
        sessions,
        tasks,
        waitingApproval: false, // phase B
      })
    }
    return map
  }, [chat.live, sessions, tasks])

  const counts = useMemo(
    () =>
      deriveStatusCounts({
        agentStatuses: statuses,
        threads: chat.threads,
        delegations: chat.delegations,
      }),
    [statuses, chat.threads, chat.delegations],
  )

  const projectActive =
    chat.live ||
    sessions.some((s) => s.status === 'starting' || s.status === 'running')

  const selectAgent = (key: AgentKey) => {
    setSelected(key)
    setOpenTabs((tabs) => (tabs.includes(key) ? tabs : [...tabs, key]))
  }

  const setView = (next: 'tree' | 'list') => {
    if (next === 'list') setSearchParams({ view: 'list' })
    else setSearchParams({})
  }

  const handleCreateThread = async () => {
    const title = window.prompt('Título del nuevo hilo', 'Nuevo hilo')
    if (!title?.trim()) return
    const t = await chat.createThread(title.trim())
    if (t) setThreadId(String(t.id))
  }

  const onPrompt = async (key: AgentKey, text: string) => {
    if (threadId && chat.detail?.status === 'open') {
      await chat.sendMessage(text, key)
      return
    }

    const openExisting = chat.threads.find((t) => t.status === 'open')
    if (openExisting) {
      const id = String(openExisting.id)
      pendingSend.current = { key, text, id }
      setThreadId(id)
      return
    }

    const t = await chat.createThread(text.slice(0, 60).trim() || 'Nuevo hilo')
    if (!t) return
    const id = String(t.id)
    pendingSend.current = { key, text, id }
    setThreadId(id)
  }

  if (view === 'list') {
    return (
      <div className="ws-list-wrap">
        <div className="ws-header">
          <h2>{project?.name ?? 'default'} — Agentes</h2>
          <div className="ws-header-actions">
            <div className="ws-seg" role="group" aria-label="Vista">
              <button type="button" onClick={() => setView('tree')}>
                Árbol
              </button>
              <button type="button" className="on">
                Lista
              </button>
            </div>
            <button
              type="button"
              className="ws-btn"
              disabled
              title="Próximamente"
            >
              Registrar agente · Próximamente
            </button>
          </div>
        </div>
        <AgentsPage />
      </div>
    )
  }

  return (
    <div className="workspace">
      <header className="ws-header">
        <h2>{project?.name ?? 'default'} — Árbol de agentes</h2>
        <span
          className={`ws-badge ${projectActive ? 'ws-badge--running' : 'ws-badge--idle'}`}
        >
          {projectActive && <span className="ws-pulse" aria-hidden="true" />}
          {projectActive ? 'Activo' : 'En reposo'}
        </span>
        <span className="ws-counts">
          <em>3</em> agentes · <em>{counts.running}</em> en curso ·{' '}
          <em>{counts.waiting}</em> en espera
          <span
            className="ws-prox"
            title="Waiting requiere aprobaciones F2.2c (fase B)"
          >
            {' '}
            (waiting: fase B)
          </span>
        </span>
        <div className="ws-header-actions">
          <div className="ws-seg" role="group" aria-label="Vista">
            <button type="button" className="on">
              Árbol
            </button>
            <button type="button" onClick={() => setView('list')}>
              Lista
            </button>
          </div>
          <button
            type="button"
            className="ws-btn"
            disabled
            title="Próximamente"
            aria-label="Registrar agente (Próximamente)"
          >
            Registrar agente · Próximamente
          </button>
        </div>
      </header>

      {loadError && (
        <div className="ws-error" role="alert">
          {loadError}
        </div>
      )}
      {chat.error && (
        <div className="ws-error" role="alert">
          {chat.error}
        </div>
      )}

      <div className="ws-body">
        <div className="ws-canvas">
          <AgentTree
            agentsByName={agentsByName}
            statuses={statuses}
            selected={selected}
            onSelect={selectAgent}
            onPrompt={onPrompt}
            promptDisabled={chat.busy}
          />
          <div className="ws-bottom-row">
            <DependenciesPanel
              threadTitle={chat.detail?.title ?? null}
              delegations={chat.delegations}
            />
            <QuickActions
              busy={chat.busy}
              live={chat.live}
              closed={chat.closed}
              hasThread={Boolean(threadId)}
              onCreateThread={() => void handleCreateThread()}
              onAdvance={chat.advance}
              onCloseThread={() => void chat.closeThread()}
            />
          </div>
        </div>

        <AgentInspector
          selectedKey={selected}
          agent={agentsByName[selected] ?? null}
          statuses={statuses}
          threads={chat.threads}
          activeThreadId={threadId}
          detail={chat.detail}
          live={chat.live}
          busy={chat.busy}
          closed={chat.closed}
          autoAdvance={chat.autoAdvance}
          advanceInfo={chat.advanceInfo}
          detailError={chat.detailError}
          streamError={chat.streamError}
          onSelectThread={setThreadId}
          onSend={async (text) => {
            await chat.sendMessage(text, 'orquestador')
          }}
          onAdvance={chat.advance}
          onCloseThread={() => void chat.closeThread()}
          onAutoAdvance={chat.setAutoAdvancePref}
          onCreateThread={() => void handleCreateThread()}
        />
      </div>

      <div className="ws-dock" aria-label="Agentes abiertos">
        <span className="ws-dock-lbl">Agentes abiertos</span>
        {openTabs.map((key) => (
          <button
            key={key}
            type="button"
            className={`ws-dock-tab${selected === key ? ' on' : ''}`}
            onClick={() => selectAgent(key)}
          >
            {agentsByName[key]?.title ??
              (key === 'orquestador' ? 'Orquestador' : key.toUpperCase())}
          </button>
        ))}
      </div>
    </div>
  )
}
