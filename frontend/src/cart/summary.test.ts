import { describe, expect, it } from 'vitest'
import type { Availability, Product } from '../api'
import {
  cartCorrections,
  cartLines,
  freeShippingMessage,
  freeShippingProgress,
  shippingPriceGrosze,
  subtotalGrosze,
} from './summary'

const product = (slug: string, name: string, price: number, variants: [number, Availability][]): Product => ({
  slug,
  name,
  tagline: '',
  category: 'swieczki',
  price_grosze: price,
  weight_g: null,
  badge: null,
  image: null,
  variants: variants.map(([id, availability]) => ({ id, name: `kolor ${id}`, hex: '#FFFFFF', availability })),
})

// "Najgorszy przypadek" from the Koszyk mockup: a very long name and 10 pieces.
const LONG_NAME = 'Zestaw prezentowy „Wieczór przy kominku” z trzema świeczkami sojowymi i drewnianymi zapałkami'
const products = [
  product('zestaw', LONG_NAME, 124900, [[1, 'available']]),
  product('mgla', 'Mgła', 999, [
    [2, 'available'],
    [3, 'sold_out'],
  ]),
  product('wanilia', 'Wanilia', 3900, [[4, 'last']]),
]

describe('cartLines', () => {
  it('joins the cart with catalogue data and keeps the cart order', () => {
    const lines = cartLines(
      [
        { variantId: 2, qty: 10 },
        { variantId: 1, qty: 1 },
      ],
      products,
    )

    expect(lines.map((l) => [l.productName, l.qty, l.lineTotalGrosze])).toEqual([
      ['Mgła', 10, 9990],
      [LONG_NAME, 1, 124900],
    ])
    expect(lines[0].max).toBe(10)
  })

  it('skips variants missing from the API', () => {
    expect(cartLines([{ variantId: 99, qty: 1 }], products)).toEqual([])
  })

  it('limits the last piece to 1 and does not count sold-out lines', () => {
    const lines = cartLines(
      [
        { variantId: 4, qty: 1 },
        { variantId: 3, qty: 2 },
      ],
      products,
    )

    expect(lines[0].max).toBe(1)
    expect(lines[1]).toMatchObject({ availability: 'sold_out', max: 0, lineTotalGrosze: 0 })
  })
})

describe('cartCorrections', () => {
  it('removes unknown variants and caps the last piece, keeping sold-out lines', () => {
    const cart = [
      { variantId: 99, qty: 1 },
      { variantId: 4, qty: 3 },
      { variantId: 3, qty: 2 },
      { variantId: 2, qty: 10 },
    ]

    expect(cartCorrections(cart, products)).toEqual([
      { variantId: 99, qty: 0 },
      { variantId: 4, qty: 1 },
    ])
  })

  it('leaves a valid cart unchanged', () => {
    expect(cartCorrections([{ variantId: 2, qty: 3 }], products)).toEqual([])
  })
})

describe('subtotal and free shipping', () => {
  it('sums line totals in grosze (worst case: 1249 zł + 10 × 9,99 zł)', () => {
    const lines = cartLines(
      [
        { variantId: 1, qty: 1 },
        { variantId: 2, qty: 10 },
      ],
      products,
    )
    expect(subtotalGrosze(lines)).toBe(134890)
    expect(subtotalGrosze([])).toBe(0)
  })

  it('shows how much is missing below the threshold', () => {
    const progress = freeShippingProgress(12000, 20000)
    expect(progress).toEqual({ reached: false, missingGrosze: 8000, ratio: 0.6 })
    expect(freeShippingMessage(progress)).toMatch(/^Brakuje 80,00\s?zł do darmowej dostawy$/)
  })

  it('is free at and above the threshold', () => {
    expect(freeShippingProgress(20000, 20000)).toEqual({ reached: true, missingGrosze: 0, ratio: 1 })
    expect(freeShippingProgress(25000, 20000).reached).toBe(true)
    expect(freeShippingMessage(freeShippingProgress(25000, 20000))).toBe('Masz darmową dostawę!')
  })
})

describe('shippingPriceGrosze', () => {
  const info = {
    methods: [{ id: 'locker' as const, name: 'Paczkomat InPost', price_grosze: 1400 }],
    free_shipping_threshold_grosze: 20000,
  }

  it('is the method price below the threshold and free from it', () => {
    expect(shippingPriceGrosze(info, 'locker', 19999)).toBe(1400)
    expect(shippingPriceGrosze(info, 'locker', 20000)).toBe(0)
  })

  it('is unknown (not free) for a method missing from the API', () => {
    expect(shippingPriceGrosze(info, 'courier', 25000)).toBeNull()
  })
})
