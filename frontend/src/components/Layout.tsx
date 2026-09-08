import { NavLink, Outlet } from 'react-router-dom'
import {
  Bot,
  Columns3,
  Files,
  Inbox,
  Moon,
  Settings,
  Sun,
  Activity,
} from 'lucide-react'
import { useEffect, useState } from 'react'

const primaryLinks = [
  { to: '/agents', label: 'Agentes', icon: Bot },
  { to: '/tasks', label: 'Tareas', icon: Columns3 },
  { to: '/sessions', label: 'Sesiones', icon: Activity },
  { to: '/inbox', label: 'Inbox', icon: Inbox },
]

const secondaryLinks = [
  { to: '/files', label: 'Archivos', icon: Files },
  { to: '/settings', label: 'Ajustes', icon: Settings },
]

export default function Layout() {
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    const saved = localStorage.getItem('gallaia-theme')
    return saved === 'dark' ? 'dark' : 'light'
  })

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('gallaia-theme', theme)
  }, [theme])

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">G</div>
          <div>
            <h1>GallaIA</h1>
            <p>AgentOS control plane</p>
          </div>
        </div>
        <nav className="nav">
          {primaryLinks.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) => (isActive ? 'active' : undefined)}
            >
              <Icon size={18} strokeWidth={1.75} />
              {label}
            </NavLink>
          ))}
          <hr className="nav-divider" />
          {secondaryLinks.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) => (isActive ? 'active' : undefined)}
            >
              <Icon size={18} strokeWidth={1.75} />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <button
            className="btn btn-ghost"
            type="button"
            onClick={() => setTheme((t) => (t === 'light' ? 'dark' : 'light'))}
          >
            {theme === 'light' ? <Moon size={16} /> : <Sun size={16} />}
            {theme === 'light' ? 'Modo oscuro' : 'Modo claro'}
          </button>
          <p style={{ marginTop: '0.75rem' }}>
            Estética atelier · light theme canónico
          </p>
        </div>
      </aside>
      <main className="main">
        <Outlet />
      </main>
    </div>
  )
}
