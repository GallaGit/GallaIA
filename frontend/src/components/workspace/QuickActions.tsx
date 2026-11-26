type Props = {
  busy: boolean
  live: boolean
  closed: boolean
  hasThread: boolean
  onCreateThread: () => void
  onAdvance: () => void
  onCloseThread: () => void
}

export default function QuickActions({
  busy,
  live,
  closed,
  hasThread,
  onCreateThread,
  onAdvance,
  onCloseThread,
}: Props) {
  return (
    <section className="ws-panel" aria-label="Acciones rápidas">
      <h3>Acciones rápidas</h3>
      <div className="ws-actions">
        <button
          type="button"
          className="ws-btn"
          onClick={onCreateThread}
          disabled={busy}
        >
          Crear hilo
        </button>
        <button
          type="button"
          className="ws-btn"
          onClick={onAdvance}
          disabled={busy || live || closed || !hasThread}
        >
          Avanzar
        </button>
        <button
          type="button"
          className="ws-btn"
          onClick={onCloseThread}
          disabled={busy || closed || !hasThread}
        >
          Cerrar hilo
        </button>
        <button
          type="button"
          className="ws-btn ws-btn-ok"
          disabled
          title="Fase B — aprobaciones F2.2c"
        >
          Aprobar
        </button>
        <button
          type="button"
          className="ws-btn ws-btn-danger"
          disabled
          title="Fase B — aprobaciones F2.2c"
        >
          Rechazar
        </button>
      </div>
      <p className="ws-soon">
        Próximamente: Crear worktree · Pausar todo · Cambiar rama
      </p>
    </section>
  )
}
