import { MAX_QTY } from '../productPage'

/** Only ids and quantities: names and prices always come from the API. */
export type CartItem = { variantId: number; qty: number }
export type Cart = CartItem[]

function clamp(qty: number, max: number): number {
  return Math.min(Math.max(Math.trunc(qty), 1), max)
}

/** Adds qty of a variant; the same variant is merged and capped (10, or 1 for the last piece). */
export function addItem(cart: Cart, variantId: number, qty: number, max = MAX_QTY): Cart {
  const limit = Math.min(max, MAX_QTY)
  const existing = cart.find((item) => item.variantId === variantId)
  if (!existing) return [...cart, { variantId, qty: clamp(qty, limit) }]
  return cart.map((item) => (item.variantId === variantId ? { variantId, qty: clamp(item.qty + qty, limit) } : item))
}

export function setQty(cart: Cart, variantId: number, qty: number): Cart {
  if (qty < 1) return removeItem(cart, variantId)
  return cart.map((item) => (item.variantId === variantId ? { variantId, qty: clamp(qty, MAX_QTY) } : item))
}

export function removeItem(cart: Cart, variantId: number): Cart {
  return cart.filter((item) => item.variantId !== variantId)
}

/** Number of pieces, shown on the cart badge. */
export function cartCount(cart: Cart): number {
  return cart.reduce((sum, item) => sum + item.qty, 0)
}
