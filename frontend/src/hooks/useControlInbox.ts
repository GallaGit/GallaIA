import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  api,
  ApiUnavailableError,
  type ControlInboxMessage,
  type InboxSseEvent,
} from '../api/client'
import { openEventStream } from '../api/sse'

function errorMessage(e: unknown): string {
  if (e instanceof ApiUnavailableError) return 'API no disponible'
  return (e as Error).message
}

/**
 * Open control-plane approvals (F2.2c) with live updates via activity SSE
 * (`event: inbox` + `inbox.*` activity types).
 */
export function useControlInbox(enabled = true) {
  const [items, setItems] = useState<ControlInboxMessage[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [decidingId, setDecidingId] = useState<number | null>(null)
  const [live, setLive] = useState(false)
  const reloadTimer = useRef<number | null>(null)

  const load = useCallback(async () => {
    if (!enabled) {
      setItems([])
      return
    }
    setLoading(true)
    try {
      const list = await api.controlInbox('open')
      setItems(Array.isArray(list) ? list : [])
      setError(null)
    } catch (e) {
      setItems([])
      setError(errorMessage(e))
    } finally {
      setLoading(false)
    }
  }, [enabled])

  const scheduleReload = useCallback(() => {
    if (reloadTimer.current != null) window.clearTimeout(reloadTimer.current)
    reloadTimer.current = window.setTimeout(() => {
      void load()
    }, 120)
  }, [load])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    if (!enabled) return
    setLive(true)
    const close = openEventStream(
      api.activityStreamUrl(),
      {
        inbox: (data) => {
          try {
            const ev = JSON.parse(data) as InboxSseEvent
            if (ev.action === 'pending' || ev.action === 'decided') {
              scheduleReload()
            }
          } catch {
            scheduleReload()
          }
        },
        activity: (data) => {
          try {
            const ev = JSON.parse(data) as { type?: string }
            if (typeof ev.type === 'string' && ev.type.startsWith('inbox.')) {
              scheduleReload()
            }
          } catch {
            /* ignore */
          }
        },
      },
      () => {
        setLive(false)
      },
    )
    return () => {
      close()
      setLive(false)
      if (reloadTimer.current != null) window.clearTimeout(reloadTimer.current)
    }
  }, [enabled, scheduleReload])

  const decide = useCallback(
    async (id: number, approved: boolean, note?: string) => {
      setDecidingId(id)
      setError(null)
      try {
        const result = await api.decideInbox(id, {
          approved,
          note: note?.trim() || null,
        })
        setItems((prev) => prev.filter((m) => m.id !== id))
        return result
      } catch (e) {
        setError(errorMessage(e))
        throw e
      } finally {
        setDecidingId(null)
        void load()
      }
    },
    [load],
  )

  const approvals = useMemo(
    () => items.filter((m) => m.kind === 'thread_approval'),
    [items],
  )

  const waitingByAgent = useMemo(() => {
    const map: Record<string, ControlInboxMessage | undefined> = {}
    for (const a of approvals) {
      const key = (a.target_agent || '').toLowerCase()
      if (key && !map[key]) map[key] = a
    }
    return map
  }, [approvals])

  return {
    items,
    approvals,
    waitingByAgent,
    loading,
    error,
    decidingId,
    live,
    reload: load,
    decide,
  }
}
