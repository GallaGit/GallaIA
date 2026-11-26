import type { ControlInboxMessage } from '../../api/client'

type Props = {
  busy: boolean
  live: boolean
  closed: boolean
  hasThread: boolean
  pendingApproval: ControlInboxMessage | null
  deciding: boolean
  onCreateThread: () => void
  onAdvance: () => void
  onCloseThread: () => void
  onApprove: () => void
  onReject: () => void
}

export default function QuickActions({
  busy,
  live,
  closed,
  hasThread,
  pendingApproval,
  deciding,
  onCreateThread,
  onAdvance,
  onCloseThread,
  onApprove,
  onReject,
}: Props) {
  const canDecide = Boolean(pendingApproval) && !deciding
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
          disabled={!canDecide}
          title={
            pendingApproval
              ? `Aprobar inbox #${pendingApproval.id}`
              : 'Sin aprobación pendiente'
          }
          onClick={onApprove}
        >
          {deciding ? '…' : 'Aprobar'}
        </button>
        <button
          type="button"
          className="ws-btn ws-btn-danger"
          disabled={!canDecide}
          title={
            pendingApproval
              ? `Rechazar inbox #${pendingApproval.id}`
              : 'Sin aprobación pendiente'
          }
          onClick={onReject}
        >
          {deciding ? '…' : 'Rechazar'}
        </button>
      </div>
      <p className="ws-soon">
        Próximamente: Crear worktree · Pausar todo · Cambiar rama
      </p>
    </section>
  )
}
