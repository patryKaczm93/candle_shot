import { describe, expect, it } from 'vitest'
import type { Availability, Product } from './api'
import { cardColour, filterAndSort, isSoldOut } from './catalog'

function product(slug: string, price: number, category: string, stock: Availability[] = ['available']): Product {
  return {
    slug,
    name: slug,
    tagline: '',
    category,
    price_grosze: price,
    weight_g: 180,
    badge: null,
    image: null,
    variants: stock.map((availability, i) => ({ id: i, name: `kolor ${i}`, hex: `#00000${i}`, availability })),
  }
}

const products = [
  product('wanilia', 4900, 'swieczki', ['available', 'last']),
  product('zestaw', 12900, 'zestawy'),
  product('dym', 3900, 'swieczki', ['sold_out']),
]

describe('filterAndSort', () => {
  it('keeps API order for "all" and "recommended"', () => {
    expect(filterAndSort(products, 'all', 'recommended').map((p) => p.slug)).toEqual(['wanilia', 'zestaw', 'dym'])
  })

  it('filters by category', () => {
    expect(filterAndSort(products, 'zestawy', 'recommended').map((p) => p.slug)).toEqual(['zestaw'])
  })

  it('"ostatnie" shows products with a last piece in any colour', () => {
    expect(filterAndSort(products, 'ostatnie', 'recommended').map((p) => p.slug)).toEqual(['wanilia'])
  })

  it('sorts by price both ways without mutating the input', () => {
    expect(filterAndSort(products, 'all', 'price-asc').map((p) => p.slug)).toEqual(['dym', 'wanilia', 'zestaw'])
    expect(filterAndSort(products, 'all', 'price-desc').map((p) => p.slug)).toEqual(['zestaw', 'wanilia', 'dym'])
    expect(products.map((p) => p.slug)).toEqual(['wanilia', 'zestaw', 'dym'])
  })

  it('returns an empty list for a category without products', () => {
    expect(filterAndSort([products[0]], 'zestawy', 'recommended')).toEqual([])
  })
})

describe('card helpers', () => {
  it('detects a fully sold-out product', () => {
    expect(isSoldOut(products[2])).toBe(true)
    expect(isSoldOut(products[0])).toBe(false)
  })

  it('shows the first colour that is still available', () => {
    expect(cardColour(product('x', 100, 'swieczki', ['sold_out', 'available']))).toBe('#000001')
  })
})
