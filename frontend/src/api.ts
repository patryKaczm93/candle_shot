// The only place that talks to the backend. Prices, stock and order status come from here.

const API_URL = import.meta.env.VITE_API_URL ?? ''

export type Availability = 'available' | 'last' | 'sold_out'

export type Variant = {
  id: number
  name: string
  hex: string
  availability: Availability
}

export type Product = {
  slug: string
  name: string
  tagline: string
  category: string
  price_grosze: number
  weight_g: number | null
  badge: string | null
  image: string | null
  variants: Variant[]
}

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, { signal, headers: { Accept: 'application/json' } })
  if (!response.ok) {
    throw new ApiError(response.status, `GET ${path} failed with ${response.status}`)
  }
  return (await response.json()) as T
}

export function fetchProducts(signal?: AbortSignal): Promise<Product[]> {
  return getJson<Product[]>('/api/products', signal)
}

export type ProductDetail = Product & {
  description: string
}

export type ShippingInfo = {
  methods: { id: 'locker' | 'courier'; name: string; price_grosze: number }[]
  free_shipping_threshold_grosze: number
}

export function fetchProduct(slug: string, signal?: AbortSignal): Promise<ProductDetail> {
  return getJson<ProductDetail>(`/api/products/${encodeURIComponent(slug)}`, signal)
}

export function fetchShipping(signal?: AbortSignal): Promise<ShippingInfo> {
  return getJson<ShippingInfo>('/api/shipping', signal)
}
