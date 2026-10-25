import { createContext } from 'react'
import type { Cart } from './cart'

export type CartContextValue = {
  items: Cart
  count: number
  add: (variantId: number, qty: number, max?: number) => void
  setQty: (variantId: number, qty: number) => void
  remove: (variantId: number) => void
  clear: () => void
  /** Cart drawer visibility. */
  isOpen: boolean
  open: () => void
  close: () => void
}

export const CartContext = createContext<CartContextValue | null>(null)
