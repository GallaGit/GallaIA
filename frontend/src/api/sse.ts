import { authFetch } from './auth'

export function openEventStream(
  url: string,
  handlers: Record<string, (data: string) => void>,
  onError?: (e: unknown) => void,
): () => void {
  const controller = new AbortController()
  let closed = false

  const run = async (): Promise<void> => {
    try {
      const res = await authFetch(url, {
        headers: { Accept: 'text/event-stream' },
        signal: controller.signal,
      })
      if (!res.ok) {
        onError?.(new Error(`HTTP ${res.status}`))
        return
      }
      if (!res.body) {
        onError?.(new Error('Streaming response has no body'))
        return
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let eventName = ''
      let dataLines: string[] = []

      const dispatch = (): void => {
        if (!dataLines.length) {
          eventName = ''
          return
        }
        const event = eventName || 'message'
        const data = dataLines.join('\n')
        eventName = ''
        dataLines = []
        handlers[event]?.(data)
      }

      while (!closed) {
        const { value, done } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        let newline = buffer.indexOf('\n')
        while (newline !== -1) {
          let line = buffer.slice(0, newline)
          buffer = buffer.slice(newline + 1)
          if (line.endsWith('\r')) line = line.slice(0, -1)

          if (line === '') {
            dispatch()
          } else if (!line.startsWith(':')) {
            const colon = line.indexOf(':')
            const field = colon === -1 ? line : line.slice(0, colon)
            let fieldValue = colon === -1 ? '' : line.slice(colon + 1)
            if (fieldValue.startsWith(' ')) fieldValue = fieldValue.slice(1)
            if (field === 'event') {
              eventName = fieldValue
            } else if (field === 'data') {
              dataLines.push(fieldValue)
            }
          }

          newline = buffer.indexOf('\n')
        }
      }

      if (dataLines.length) dispatch()
    } catch (e) {
      if (!closed && !controller.signal.aborted) onError?.(e)
    }
  }

  void run()

  return () => {
    closed = true
    controller.abort()
  }
}
