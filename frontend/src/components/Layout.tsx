import { NavLink, Outlet, useLocation } from 'react-router-dom'
import {
  Bot,
  Columns3,
  Files,
  FolderGit2,
  FolderKanban,
  Inbox,
  Moon,
  Search,
  Settings,
  Sun,
  Activity,
  Radio,
  Eye,
  MessagesSquare,
  GitBranch,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import {
  api,
  type Project,
  type Session,
  type Task,
  type Thread,
} from '../api/client'
import {
  deriveAgentStatus,
  deriveStatusCounts,
} from '../lib/agentStatus'

const primaryLinks = [
  { to: '/agents', label: 'Agentes', icon: Bot, soon: false },
  { to: '/threads', label: 'Conversaciones', icon: MessagesSquare, soon: false },
  {
    to: '/worktrees',
    label: 'Worktrees',
    icon: FolderGit2,
    soon: true,
  },
  { to: '/tasks', label: 'Tareas', icon: Columns3, soon: false },
  { to: '/sessions', label: 'Sesiones', icon: Activity, soon: false },
  { to: '/inbox', label: 'Inbox', icon: Inbox, soon: false },
  { to: '/activity', label: 'Activity', icon: Radio, soon: false },
  { to: '/live', label: 'Live', icon: Eye, soon: false },
]

const secondaryLinks = [
  { to: '/files', label: 'Archivos', icon: Files, soon: false },
  {
    to: '/search',
    label: 'Buscar',
    icon: Search,
    soon: true,
  },
  { to: '/settings', label: 'Ajustes', icon: Settings, soon: false },
]

export default function Layout() {
  const location = useLocation()
  const isWorkspace =
    location.pathname === '/agents' || location.pathname === '/'

  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    const saved = localStorage.getItem('gallaia-theme')
    if (saved === 'light' || saved === 'dark') return saved
    return 'dark'
  })

  const [project, setProject] = useState<Project | null>(null)
  const [counts, setCounts] = useState({
    running: 0,
    waiting: 0,
    blocked: 0,
    completed: 0,
    paused: 0,
  })

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('gallaia-theme', theme)
  }, [theme])

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const [projects, sessions, tasks, threads] = await Promise.all([
          api.projects().catch(() => [] as Project[]),
          api.sessions().catch(() => [] as Session[]),
          api.tasks().catch(() => [] as Task[]),
          api.threads().catch(() => [] as Thread[]),
        ])
        if (cancelled) return
        const preferred =
          projects.find((p) => p.slug === 'default') ?? projects[0] ?? null
        setProject(preferred)
        const agentNames = ['orquestador', 'fe', 'be'] as const
        const statuses = Object.fromEntries(
          agentNames.map((name) => [
            name,
            deriveAgentStatus({
              agentName: name,
              liveStreaming: false,
              sessions,
              tasks,
              waitingApproval: false,
            }),
          ]),
        )
        setCounts(
          deriveStatusCounts({
            agentStatuses: statuses,
            threads,
            delegations: null,
          }),
        )
      } catch {
        if (!cancelled) setProject(null)
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [location.pathname])

  return (
    <div className={`app-shell${isWorkspace ? ' app-shell--workspace' : ''}`}>
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">G</div>
          <div>
            <h1>GallaIA</h1>
            <p>Equipo agéntico personal · v2</p>
          </div>
        </div>
        <nav className="nav" aria-label="Principal">
          {primaryLinks.map(({ to, label, icon: Icon, soon }) =>
            soon ? (
              <span key={to} className="nav-soon" aria-disabled="true">
                <Icon size={18} strokeWidth={1.75} />
                {label}
                <em className="ws-prox">Próx.</em>
              </span>
            ) : (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) => (isActive ? 'active' : undefined)}
              >
                <Icon size={18} strokeWidth={1.75} />
                {label}
              </NavLink>
            ),
          )}
          <hr className="nav-divider" />
          <span className="nav-soon" aria-disabled="true">
            <FolderKanban size={18} strokeWidth={1.75} />
            Proyecto
            <em className="ws-prox">vía pie</em>
          </span>
          {secondaryLinks.map(({ to, label, icon: Icon, soon }) =>
            soon ? (
              <span key={to} className="nav-soon" aria-disabled="true">
                <Icon size={18} strokeWidth={1.75} />
                {label}
                <em className="ws-prox">Próx.</em>
              </span>
            ) : (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) => (isActive ? 'active' : undefined)}
              >
                <Icon size={18} strokeWidth={1.75} />
                {label}
              </NavLink>
            ),
          )}
        </nav>

        <div className="status-box" aria-label="Estado en vivo">
          <h2>Estado en vivo</h2>
          <div className="stat">
            <span>
              <i className="dot run" />
              En curso
            </span>
            <b>{counts.running}</b>
          </div>
          <div className="stat">
            <span>
              <i className="dot wait" />
              En espera
            </span>
            <b>{counts.waiting}</b>
          </div>
          <div className="stat">
            <span>
              <i className="dot block" />
              Bloqueados
            </span>
            <b>{counts.blocked}</b>
          </div>
          <div className="stat">
            <span>
              <i className="dot ok" />
              Completados
            </span>
            <b>{counts.completed}</b>
          </div>
          <div className="stat">
            <span>
              <i className="dot pause" />
              Pausados
            </span>
            <b>{counts.paused}</b>
          </div>
          <p className="ws-hint" style={{ marginTop: 8 }}>
            Waiting/Paused: fase B (sin inventar datos)
          </p>
        </div>

        <div className="sidebar-footer">
          <button
            className="btn btn-ghost"
            type="button"
            onClick={() => setTheme((t) => (t === 'light' ? 'dark' : 'light'))}
          >
            {theme === 'light' ? <Moon size={16} /> : <Sun size={16} />}
            {theme === 'light' ? 'Modo oscuro' : 'Modo claro'}
          </button>
          <div className="side-project">
            <strong>
              Proyecto actual: {project?.name ?? 'default'}
            </strong>
            <span>
              <GitBranch size={12} aria-hidden="true" /> rama: no disponible
              <em className="ws-prox"> (placeholder)</em>
            </span>
          </div>
        </div>
      </aside>
      <main className={`main${isWorkspace ? ' main--workspace' : ''}`}>
        <Outlet />
      </main>
    </div>
  )
}
