import { MAX_QTY } from '../productPage'
import type { Cart } from './cart'

export const CART_STORAGE_KEY = 'pachnie-milo:cart:v1'

function isPositiveInt(value: unknown): value is number {
  return typeof value === 'number' && Number.isInteger(value) && value > 0
}

/** Anything can be in localStorage (old versions, manual edits): keep only valid lines. */
export function parseCart(raw: string | null): Cart {
  if (!raw) return []
  let data: unknown
  try {
    data = JSON.parse(raw)
  } catch {
    return []
  }
  if (!Array.isArray(data)) return []

  const cart: Cart = []
  for (const entry of data) {
    if (typeof entry !== 'object' || entry === null) continue
    const { variantId, qty } = entry as Record<string, unknown>
    if (!isPositiveInt(variantId) || !isPositiveInt(qty)) continue
    if (cart.some((item) => item.variantId === variantId)) continue
    cart.push({ variantId, qty: Math.min(qty, MAX_QTY) })
  }
  return cart
}

// Storage can throw (private mode, quota, blocked cookies); the cart then lives only in memory.
export function loadCart(storage: Storage | undefined): Cart {
  try {
    return parseCart(storage?.getItem(CART_STORAGE_KEY) ?? null)
  } catch {
    return []
  }
}

export function saveCart(storage: Storage | undefined, cart: Cart): void {
  try {
    storage?.setItem(CART_STORAGE_KEY, JSON.stringify(cart))
  } catch {
    // Ignore: see loadCart.
  }
}

export function browserStorage(): Storage | undefined {
  try {
    return typeof window === 'undefined' ? undefined : window.localStorage
  } catch {
    return undefined
  }
}
