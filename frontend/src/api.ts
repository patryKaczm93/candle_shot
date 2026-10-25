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

export type CheckoutRequest = {
  email: string
  phone: string
  full_name: string
  shipping:
    | { method: 'locker'; locker_id: string }
    | { method: 'courier'; address_line: string; postal_code: string; city: string }
  invoice: { nip: string; name: string } | null
  terms_accepted: boolean
  items: { variant_id: number; qty: number }[]
}

/** Error from POST /api/checkout; `detail` is text, a list of field errors (422) or an object (409). */
export class CheckoutError extends ApiError {
  readonly detail: unknown

  constructor(status: number, detail: unknown) {
    super(status, `POST /api/checkout failed with ${status}`)
    this.detail = detail
  }
}

const STRIPE_CHECKOUT_ORIGIN = 'https://checkout.stripe.com/'
const CHECKOUT_TIMEOUT_MS = 30_000

/** Only a Stripe Checkout address may be used for the redirect. */
export function isStripeCheckoutUrl(url: unknown): url is string {
  return typeof url === 'string' && url.startsWith(STRIPE_CHECKOUT_ORIGIN)
}

/** Creates the order and returns the Stripe Checkout URL. Prices are set by the backend. */
export async function postCheckout(body: CheckoutRequest): Promise<{ url: string }> {
  const response = await fetch(`${API_URL}/api/checkout`, {
    method: 'POST',
    headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(CHECKOUT_TIMEOUT_MS),
  })
  const data: unknown = await response.json().catch(() => null)
  if (!response.ok) {
    throw new CheckoutError(response.status, (data as { detail?: unknown } | null)?.detail)
  }
  const url = (data as { url?: unknown } | null)?.url
  if (!isStripeCheckoutUrl(url)) throw new CheckoutError(500, undefined)
  return { url }
}
