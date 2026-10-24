import { describe, expect, it } from 'vitest'
import type { Variant } from './api'
import { addLabel, canAdd, clampQty, initialVariant, maxQty, qtyLabel } from './productPage'

const variant = (id: number, availability: Variant['availability']): Variant => ({
  id,
  name: `kolor ${id}`,
  hex: '#FFFFFF',
  availability,
})

describe('add button', () => {
  it('is disabled for a sold-out colour (stock = 0)', () => {
    expect(canAdd('sold_out')).toBe(false)
    expect(maxQty('sold_out')).toBe(0)
  })

  it('is enabled for available and last-piece colours', () => {
    expect(canAdd('available')).toBe(true)
    expect(canAdd('last')).toBe(true)
  })
})

describe('quantity', () => {
  it('allows 1–10 for an available colour', () => {
    expect(maxQty('available')).toBe(10)
    expect(clampQty(0, 'available')).toBe(1)
    expect(clampQty(11, 'available')).toBe(10)
    expect(clampQty(4, 'available')).toBe(4)
  })

  it('allows only 1 for the last piece, also after switching colour', () => {
    expect(maxQty('last')).toBe(1)
    expect(clampQty(6, 'last')).toBe(1)
  })
})

describe('initialVariant', () => {
  it('skips sold-out colours', () => {
    expect(initialVariant([variant(1, 'sold_out'), variant(2, 'last')])?.id).toBe(2)
  })

  it('falls back to the first colour when everything is sold out', () => {
    expect(initialVariant([variant(1, 'sold_out'), variant(2, 'sold_out')])?.id).toBe(1)
  })

  it('handles a product without colours', () => {
    expect(initialVariant([])).toBeUndefined()
  })
})

describe('labels', () => {
  it('names the quantity on the button', () => {
    expect(addLabel(1)).toBe('Dodaj do koszyka')
    expect(addLabel(3)).toBe('Dodaj 3 do koszyka')
  })

  it('uses Polish plural forms', () => {
    expect(qtyLabel(1)).toBe('1 sztuka')
    expect(qtyLabel(2)).toBe('2 sztuki')
    expect(qtyLabel(5)).toBe('5 sztuk')
  })
})
