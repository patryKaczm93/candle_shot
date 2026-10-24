import type { Product } from './api'

export type CategoryId = 'all' | 'swieczki' | 'zestawy' | 'ostatnie'
export type SortId = 'recommended' | 'price-asc' | 'price-desc'

export const CATEGORIES: { id: CategoryId; label: string }[] = [
  { id: 'all', label: 'Wszystkie' },
  { id: 'swieczki', label: 'Świeczki' },
  { id: 'zestawy', label: 'Zestawy prezentowe' },
  { id: 'ostatnie', label: 'Ostatnie sztuki' },
]

export const SORTS: { id: SortId; label: string }[] = [
  { id: 'recommended', label: 'Polecane' },
  { id: 'price-asc', label: 'Cena: od najniższej' },
  { id: 'price-desc', label: 'Cena: od najwyższej' },
]

export function isCategoryId(value: string | null): value is CategoryId {
  return CATEGORIES.some((category) => category.id === value)
}

export function isSoldOut(product: Product): boolean {
  return product.variants.length > 0 && product.variants.every((v) => v.availability === 'sold_out')
}

/** Plaster colour shown on the card: the first one that can still be bought. */
export function cardColour(product: Product): string {
  const variant = product.variants.find((v) => v.availability !== 'sold_out') ?? product.variants[0]
  return variant?.hex ?? '#FFFFFF'
}

/** Products keep the API order ("Polecane"); filtering and sorting are display only. */
export function filterAndSort(products: Product[], category: CategoryId, sort: SortId): Product[] {
  const shown = products.filter((product) => {
    if (category === 'all') return true
    if (category === 'ostatnie') return product.variants.some((v) => v.availability === 'last')
    return product.category === category
  })
  if (sort === 'price-asc') return [...shown].sort((a, b) => a.price_grosze - b.price_grosze)
  if (sort === 'price-desc') return [...shown].sort((a, b) => b.price_grosze - a.price_grosze)
  return shown
}
