import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import AgentsPage from './pages/AgentsPage'
import TasksPage from './pages/TasksPage'
import SessionsPage from './pages/SessionsPage'
import InboxPage from './pages/InboxPage'
import PlaceholderPage from './pages/PlaceholderPage'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Navigate to="/tasks" replace />} />
        <Route path="agents" element={<AgentsPage />} />
        <Route path="agents/:id" element={<AgentsPage />} />
        <Route path="tasks" element={<TasksPage />} />
        <Route path="sessions" element={<SessionsPage />} />
        <Route path="sessions/:id" element={<SessionsPage />} />
        <Route path="inbox" element={<InboxPage />} />
        <Route
          path="files"
          element={
            <PlaceholderPage
              title="Archivos"
              blurb="Navegador R2 / filesystem MCP — Phase 2+. Placeholder en Phase 1."
            />
          }
        />
        <Route
          path="settings"
          element={
            <PlaceholderPage
              title="Ajustes"
              blurb="YAML sync, runners, secretos — más adelante. Phase 1 usa SQLite + mock runner."
            />
          }
        />
      </Route>
    </Routes>
  )
}
