import type { Availability, Product, ShippingInfo } from '../api'
import { formatPrice } from '../format'
import { maxQty } from '../productPage'
import type { Cart } from './cart'

/** A cart line joined with catalogue data. Prices are informational; the backend recalculates them. */
export type CartLine = {
  variantId: number
  slug: string
  productName: string
  variantName: string
  hex: string
  availability: Availability
  unitPriceGrosze: number
  qty: number
  max: number
  lineTotalGrosze: number
}

function findVariant(products: Product[], variantId: number) {
  for (const product of products) {
    const variant = product.variants.find((v) => v.id === variantId)
    if (variant) return { product, variant }
  }
  return undefined
}

/** Cart lines in cart order; variants missing from the API are skipped. */
export function cartLines(cart: Cart, products: Product[]): CartLine[] {
  const lines: CartLine[] = []
  for (const item of cart) {
    const found = findVariant(products, item.variantId)
    if (!found) continue
    const { product, variant } = found
    const soldOut = variant.availability === 'sold_out'
    lines.push({
      variantId: variant.id,
      slug: product.slug,
      productName: product.name,
      variantName: variant.name,
      hex: variant.hex,
      availability: variant.availability,
      unitPriceGrosze: product.price_grosze,
      qty: item.qty,
      max: maxQty(variant.availability),
      lineTotalGrosze: soldOut ? 0 : product.price_grosze * item.qty,
    })
  }
  return lines
}

/**
 * Quantity changes the cart needs after loading the catalogue: qty 0 removes a variant the API no longer has,
 * otherwise the qty is capped (1 for the last piece). Sold-out lines stay, so the customer sees why.
 */
export function cartCorrections(cart: Cart, products: Product[]): Cart {
  const corrections: Cart = []
  for (const item of cart) {
    const found = findVariant(products, item.variantId)
    if (!found) {
      corrections.push({ variantId: item.variantId, qty: 0 })
      continue
    }
    const max = maxQty(found.variant.availability)
    if (max > 0 && item.qty > max) corrections.push({ variantId: item.variantId, qty: max })
  }
  return corrections
}

export function subtotalGrosze(lines: CartLine[]): number {
  return lines.reduce((sum, line) => sum + line.lineTotalGrosze, 0)
}

export type FreeShippingProgress = {
  reached: boolean
  missingGrosze: number
  /** 0–1, width of the progress bar. */
  ratio: number
}

export function freeShippingProgress(subtotal: number, threshold: number): FreeShippingProgress {
  if (threshold <= 0 || subtotal >= threshold) return { reached: true, missingGrosze: 0, ratio: 1 }
  return { reached: false, missingGrosze: threshold - subtotal, ratio: subtotal / threshold }
}

export function freeShippingMessage(progress: FreeShippingProgress): string {
  if (progress.reached) return 'Masz darmową dostawę!'
  return `Brakuje ${formatPrice(progress.missingGrosze)} do darmowej dostawy`
}

/** Shipping shown in the order summary; the backend computes the amount actually charged. */
export function shippingPriceGrosze(
  info: ShippingInfo,
  method: 'locker' | 'courier',
  subtotal: number,
): number | null {
  const price = info.methods.find((m) => m.id === method)?.price_grosze
  if (price === undefined) return null
  return freeShippingProgress(subtotal, info.free_shipping_threshold_grosze).reached ? 0 : price
}
