import { useCallback, useEffect, useState } from 'react'
import { ApiError } from './api'

export type ApiState<T> =
  | { status: 'loading' }
  | { status: 'not-found' }
  | { status: 'error' }
  | { status: 'ready'; data: T }

/** Loads data once per `key`; `reload` retries after an error. */
export function useApi<T>(load: (signal: AbortSignal) => Promise<T>, key: string): ApiState<T> & { reload: () => void } {
  const [state, setState] = useState<ApiState<T>>({ status: 'loading' })
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    setState({ status: 'loading' })
    load(controller.signal)
      .then((data) => setState({ status: 'ready', data }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return
        setState({ status: error instanceof ApiError && error.status === 404 ? 'not-found' : 'error' })
      })
    return () => controller.abort()
    // `load` is recreated on every render; `key` identifies what to load.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, attempt])

  const reload = useCallback(() => setAttempt((n) => n + 1), [])
  return { ...state, reload }
}
