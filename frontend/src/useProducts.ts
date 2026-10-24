import { fetchProducts } from './api'
import { useApi } from './useApi'

export function useProducts() {
  return useApi(fetchProducts, 'products')
}
