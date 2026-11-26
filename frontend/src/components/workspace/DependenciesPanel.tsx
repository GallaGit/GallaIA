import type { ThreadDelegations } from '../../api/client'

type Props = {
  threadTitle: string | null
  delegations: ThreadDelegations | null
}

/**
 * Phase A: lightweight list from GET /threads/{id}/delegations.
 * Rich Architecture→QA diagram from the template is out of scope.
 */
export default function DependenciesPanel({
  threadTitle,
  delegations,
}: Props) {
  return (
    <section className="ws-panel" aria-label="Dependencias y flujo">
      <h3>
        Dependencias y flujo
        {threadTitle ? ` · ${threadTitle}` : ''}
      </h3>
      {!threadTitle && (
        <div className="ws-empty compact">Elige o crea un hilo</div>
      )}
      {threadTitle && (!delegations || !delegations.edges.length) && (
        <div className="ws-empty compact">Sin delegaciones todavía</div>
      )}
      {delegations && delegations.edges.length > 0 && (
        <ul className="ws-flow-list">
          {delegations.edges.map((e) => (
            <li key={e.delegation_id}>
              <span className="mono">
                {e.source} → {e.target}
              </span>
              <span
                className={`ws-badge ws-badge--${
                  e.status === 'answered' ? 'completed' : 'running'
                }`}
              >
                {e.status === 'answered' ? 'respondida' : 'pendiente'}
              </span>
              <span title={e.brief}>
                {e.brief.length > 72 ? `${e.brief.slice(0, 72)}…` : e.brief}
              </span>
            </li>
          ))}
        </ul>
      )}
      {delegations?.summary_id != null && (
        <p className="ws-muted-line">Resumen enviado al usuario</p>
      )}
      <p className="ws-hint">
        graph-state / pending_approval · placeholder (fase B/C)
      </p>
    </section>
  )
}
