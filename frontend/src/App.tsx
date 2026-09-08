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
        <Route index element={<Navigate to="/agents" replace />} />
        <Route path="agents" element={<AgentsPage />} />
        <Route path="agents/:name" element={<AgentsPage />} />
        <Route path="tasks" element={<TasksPage />} />
        <Route path="sessions" element={<SessionsPage />} />
        <Route path="sessions/:id" element={<SessionsPage />} />
        <Route path="inbox" element={<InboxPage />} />
        <Route
          path="files"
          element={
            <PlaceholderPage
              title="Archivos"
              blurb="Próximamente — navegador de archivos / MCP filesystem."
            />
          }
        />
        <Route
          path="settings"
          element={
            <PlaceholderPage
              title="Ajustes"
              blurb="Próximamente — runners, secretos y sync."
            />
          }
        />
      </Route>
    </Routes>
  )
}
