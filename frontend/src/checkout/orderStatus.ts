import type { OrderSummary } from '../api'

/** How often the thank-you page asks for the order status, and for how long. */
export const POLL_INTERVAL_MS = 2000
export const MAX_POLLS = 60 // 2 minutes; a bank transfer can take much longer.

/** Result of one GET /api/orders/by-session/{id}. */
export type OrderLookup =
  | { state: 'loading' }
  | { state: 'missing' } // 404: no order for this session, nothing to wait for
  | { state: 'error' } // network or server error, worth retrying
  | { state: 'found'; order: OrderSummary }

export type ThankYouView =
  | { kind: 'checking' }
  | { kind: 'paid'; number: string }
  | { kind: 'waiting'; number: string }
  | { kind: 'slow'; number: string | null }
  | { kind: 'cancelled'; number: string }
  | { kind: 'refunded'; number: string }
  | { kind: 'unknown' }

/** True while the page should ask again: the payment may still be confirmed by the webhook. */
export function shouldPoll(lookup: OrderLookup, polls: number): boolean {
  if (polls >= MAX_POLLS) return false
  if (lookup.state === 'missing') return false
  if (lookup.state === 'found') return lookup.order.status === 'pending'
  return true
}

/** What the thank-you page shows. The status comes only from the backend. */
export function thankYouView(lookup: OrderLookup, polls: number): ThankYouView {
  const givenUp = polls >= MAX_POLLS

  switch (lookup.state) {
    case 'missing':
      return { kind: 'unknown' }
    case 'loading':
      return { kind: 'checking' }
    case 'error':
      return givenUp ? { kind: 'slow', number: null } : { kind: 'checking' }
    case 'found': {
      const { number, status } = lookup.order
      if (status === 'paid' || status === 'shipped') return { kind: 'paid', number }
      if (status === 'cancelled') return { kind: 'cancelled', number }
      if (status === 'refunded') return { kind: 'refunded', number }
      return givenUp ? { kind: 'slow', number } : { kind: 'waiting', number }
    }
  }
}
