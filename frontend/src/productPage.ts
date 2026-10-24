import type { Availability, Variant } from './api'
import { pluralPl } from './format'

export const MAX_QTY = 10

/** Colour selected when the page opens: the first one that can still be bought. */
export function initialVariant(variants: Variant[]): Variant | undefined {
  return variants.find((v) => v.availability !== 'sold_out') ?? variants[0]
}

/** Highest quantity the UI offers; the backend checks real stock again at checkout. */
export function maxQty(availability: Availability): number {
  if (availability === 'sold_out') return 0
  if (availability === 'last') return 1
  return MAX_QTY
}

export function clampQty(qty: number, availability: Availability): number {
  const max = maxQty(availability)
  if (max === 0) return 1
  return Math.min(Math.max(qty, 1), max)
}

export function canAdd(availability: Availability): boolean {
  return maxQty(availability) > 0
}

export const STOCK_LABELS: Record<Availability, string> = {
  available: 'Dostępna',
  last: 'Ostatnia sztuka',
  sold_out: 'Wyprzedana',
}

export function addLabel(qty: number): string {
  return qty === 1 ? 'Dodaj do koszyka' : `Dodaj ${qty} do koszyka`
}

export function qtyLabel(qty: number): string {
  return `${qty} ${pluralPl(qty, ['sztuka', 'sztuki', 'sztuk'])}`
}
