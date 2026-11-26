import { useCallback, useEffect, useRef, useState } from 'react'
import {
  api,
  ApiUnavailableError,
  type Thread,
  type ThreadDelegations,
  type ThreadDetail,
  type ThreadMessage,
} from '../api/client'
import { openEventStream } from '../api/sse'

const AUTO_ADVANCE_KEY = 'gallaia.autoAdvance'
export const MAX_MESSAGE_CHARS = 20000

function mergeMessages(
  prev: ThreadMessage[],
  incoming: ThreadMessage[],
): { merged: ThreadMessage[]; added: number } {
  const ids = new Set(prev.map((m) => m.id))
  const fresh = incoming.filter((m) => !ids.has(m.id))
  if (!fresh.length) return { merged: prev, added: 0 }
  return {
    merged: [...prev, ...fresh].sort((a, b) => a.id - b.id),
    added: fresh.length,
  }
}

function loadAutoAdvance(): boolean {
  try {
    const raw = localStorage.getItem(AUTO_ADVANCE_KEY)
    return raw === null ? true : raw !== 'false'
  } catch {
    return true
  }
}

function errorMessage(e: unknown): string {
  if (e instanceof ApiUnavailableError) return 'API no disponible'
  return (e as Error).message
}

/** Prefix for FE/BE card prompts — always addressed to the Orquestador. */
export function messageForOrchestrator(
  text: string,
  targetAgent?: 'fe' | 'be' | 'orquestador',
): string {
  const body = text.trim()
  if (!targetAgent || targetAgent === 'orquestador') return body
  const label = targetAgent.toUpperCase()
  return `[Destino: ${label}] ${body}`
}

export function useActiveThread(threadId: string | null) {
  const [threads, setThreads] = useState<Thread[]>([])
  const [detail, setDetail] = useState<ThreadDetail | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [detailError, setDetailError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [advanceInfo, setAdvanceInfo] = useState<string | null>(null)
  const [streamKey, setStreamKey] = useState(0)
  const [live, setLive] = useState(false)
  const [streamFor, setStreamFor] = useState<string | null>(null)
  const [streamError, setStreamError] = useState<string | null>(null)
  const [delegations, setDelegations] = useState<ThreadDelegations | null>(null)
  const [autoAdvance, setAutoAdvance] = useState<boolean>(loadAutoAdvance)
  const addedRef = useRef(0)

  const loadThreads = useCallback(async () => {
    try {
      const list = await api.threads()
      setThreads(Array.isArray(list) ? list : [])
      setError(null)
    } catch (e) {
      setThreads([])
      setError(errorMessage(e))
    }
  }, [])

  const loadDetail = useCallback(async (id: string) => {
    setDetailError(null)
    try {
      const d = await api.thread(id)
      setDetail(d)
    } catch (e) {
      setDetail(null)
      setDetailError(errorMessage(e))
    }
  }, [])

  const loadDelegations = useCallback(async (id: string) => {
    try {
      const d = await api.getThreadDelegations(id)
      setDelegations(d)
    } catch {
      setDelegations(null)
    }
  }, [])

  useEffect(() => {
    void loadThreads()
  }, [loadThreads])

  useEffect(() => {
    setAdvanceInfo(null)
    setDetailError(null)
    setStreamError(null)
    setStreamFor(null)
    setDelegations(null)
    if (!threadId) {
      setDetail(null)
      return
    }
    void loadDetail(threadId)
    void loadDelegations(threadId)
  }, [threadId, loadDetail, loadDelegations])

  useEffect(() => {
    if (!live && threadId) void loadDelegations(threadId)
  }, [live, threadId, loadDelegations])

  useEffect(() => {
    if (!threadId || streamFor !== String(threadId) || streamKey === 0) return
    addedRef.current = 0
    setLive(true)
    const close = openEventStream(
      api.threadStreamUrl(threadId, 6),
      {
        message: (data) => {
          try {
            const msg = JSON.parse(data) as ThreadMessage
            setDetail((prev) => {
              if (!prev || String(prev.id) !== String(threadId)) return prev
              const { merged, added } = mergeMessages(prev.messages, [msg])
              if (added > 0) addedRef.current += added
              return added > 0 ? { ...prev, messages: merged } : prev
            })
          } catch {
            /* ignore malformed frames */
          }
        },
        end: (data) => {
          try {
            const parsed = JSON.parse(data) as { created?: number }
            const n =
              typeof parsed.created === 'number'
                ? parsed.created
                : addedRef.current
            setAdvanceInfo(
              n === 0
                ? 'Sin respuestas pendientes'
                : n === 1
                  ? '1 respuesta nueva'
                  : `${n} respuestas nuevas`,
            )
          } catch {
            setAdvanceInfo(null)
          }
          setLive(false)
          close()
        },
        error: (data) => {
          if (data) {
            try {
              const body = JSON.parse(data) as { message?: string }
              setDetailError(body.message ?? data)
            } catch {
              setDetailError(data)
            }
            setLive(false)
            close()
          }
        },
      },
      () => {
        close()
        setLive(false)
        setStreamError(
          'Se perdió la conexión en directo. Pulsa Avanzar para reintentar.',
        )
      },
    )

    return () => {
      close()
      setLive(false)
    }
  }, [threadId, streamKey, streamFor])

  const createThread = async (title: string): Promise<Thread | null> => {
    if (!title.trim() || busy) return null
    setBusy(true)
    setError(null)
    try {
      const t = await api.createThread(title.trim())
      await loadThreads()
      return t
    } catch (e) {
      setError(errorMessage(e))
      return null
    } finally {
      setBusy(false)
    }
  }

  const sendMessage = async (
    text: string,
    targetAgent?: 'fe' | 'be' | 'orquestador',
  ): Promise<boolean> => {
    if (!threadId || !text.trim() || busy || detail?.status === 'closed') {
      return false
    }
    const body = messageForOrchestrator(text, targetAgent)
    if (body.length > MAX_MESSAGE_CHARS) {
      setDetailError(
        `El mensaje supera el límite de ${MAX_MESSAGE_CHARS} caracteres`,
      )
      return false
    }
    setBusy(true)
    setAdvanceInfo(null)
    setDetailError(null)
    try {
      const msg = await api.postThreadMessage(threadId, body)
      setDetail((prev) =>
        prev && String(prev.id) === String(threadId)
          ? { ...prev, messages: mergeMessages(prev.messages, [msg]).merged }
          : prev,
      )
      if (autoAdvance) {
        setStreamError(null)
        setStreamFor(String(threadId))
        setStreamKey((k) => k + 1)
      } else {
        void loadDelegations(threadId)
      }
      return true
    } catch (e) {
      setDetailError(errorMessage(e))
      return false
    } finally {
      setBusy(false)
    }
  }

  const setAutoAdvancePref = (checked: boolean) => {
    setAutoAdvance(checked)
    try {
      localStorage.setItem(AUTO_ADVANCE_KEY, String(checked))
    } catch {
      /* ignore */
    }
  }

  const advance = () => {
    if (!threadId || busy || live || detail?.status === 'closed') return
    setDetailError(null)
    setAdvanceInfo('Transmitiendo en directo…')
    setStreamError(null)
    setStreamFor(String(threadId))
    setStreamKey((k) => k + 1)
  }

  const closeThread = async (): Promise<boolean> => {
    if (!threadId || busy || detail?.status === 'closed') return false
    setBusy(true)
    setAdvanceInfo(null)
    setDetailError(null)
    try {
      await api.closeThread(threadId)
      await loadThreads()
      await loadDetail(threadId)
      await loadDelegations(threadId)
      setStreamFor(null)
      return true
    } catch (e) {
      setDetailError(errorMessage(e))
      return false
    } finally {
      setBusy(false)
    }
  }

  const ensureOpenThread = async (
    titleFallback = 'Nuevo hilo',
  ): Promise<string | null> => {
    if (threadId && detail?.status === 'open') return threadId
    const open = threads.find((t) => t.status === 'open')
    if (open) return String(open.id)
    const created = await createThread(titleFallback)
    return created ? String(created.id) : null
  }

  return {
    threads,
    detail,
    error,
    detailError,
    busy,
    live,
    advanceInfo,
    streamError,
    delegations,
    autoAdvance,
    closed: detail?.status === 'closed',
    loadThreads,
    createThread,
    sendMessage,
    setAutoAdvancePref,
    advance,
    closeThread,
    ensureOpenThread,
  }
}
