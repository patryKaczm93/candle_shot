import { useCallback, useEffect, useState } from 'react'
import { fetchProducts, type Product } from './api'

type ProductsState =
  | { status: 'loading' }
  | { status: 'error' }
  | { status: 'ready'; products: Product[] }

export function useProducts(): ProductsState & { reload: () => void } {
  const [state, setState] = useState<ProductsState>({ status: 'loading' })
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    fetchProducts(controller.signal)
      .then((products) => setState({ status: 'ready', products }))
      .catch(() => {
        if (!controller.signal.aborted) setState({ status: 'error' })
      })
    return () => controller.abort()
  }, [attempt])

  const reload = useCallback(() => {
    setState({ status: 'loading' })
    setAttempt((n) => n + 1)
  }, [])

  return { ...state, reload }
}
