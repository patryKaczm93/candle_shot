import { describe, expect, it } from 'vitest'
import { addItem, cartCount, removeItem, setQty } from './cart'

describe('cart', () => {
  it('adds a new variant', () => {
    expect(addItem([], 7, 2)).toEqual([{ variantId: 7, qty: 2 }])
  })

  it('merges the same variant and caps it at 10', () => {
    expect(addItem([{ variantId: 7, qty: 8 }], 7, 5)).toEqual([{ variantId: 7, qty: 10 }])
  })

  it('caps the last piece at 1', () => {
    expect(addItem([{ variantId: 7, qty: 1 }], 7, 1, 1)).toEqual([{ variantId: 7, qty: 1 }])
  })

  it('never lets the max exceed 10', () => {
    expect(addItem([], 7, 50, 99)).toEqual([{ variantId: 7, qty: 10 }])
  })

  it('changes quantity within 1–10 and removes at 0', () => {
    const cart = [
      { variantId: 1, qty: 2 },
      { variantId: 2, qty: 1 },
    ]
    expect(setQty(cart, 1, 12)).toEqual([
      { variantId: 1, qty: 10 },
      { variantId: 2, qty: 1 },
    ])
    expect(setQty(cart, 1, 0)).toEqual([{ variantId: 2, qty: 1 }])
  })

  it('removes a variant and counts pieces', () => {
    const cart = [
      { variantId: 1, qty: 2 },
      { variantId: 2, qty: 3 },
    ]
    expect(removeItem(cart, 1)).toEqual([{ variantId: 2, qty: 3 }])
    expect(cartCount(cart)).toBe(5)
    expect(cartCount([])).toBe(0)
  })
})
