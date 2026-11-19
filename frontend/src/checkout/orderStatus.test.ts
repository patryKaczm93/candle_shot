import { describe, expect, it } from 'vitest'
import type { OrderSummary } from '../api'
import { MAX_POLLS, shouldPoll, thankYouView, type OrderLookup } from './orderStatus'

const found = (status: OrderSummary['status']): OrderLookup => ({
  state: 'found',
  order: { number: 'PM-7K3QX9', status },
})

describe('shouldPoll', () => {
  it('keeps polling while the order is pending', () => {
    expect(shouldPoll(found('pending'), 1)).toBe(true)
  })

  it('stops once the order is paid or cancelled', () => {
    expect(shouldPoll(found('paid'), 1)).toBe(false)
    expect(shouldPoll(found('cancelled'), 1)).toBe(false)
  })

  it('retries after a network error', () => {
    expect(shouldPoll({ state: 'error' }, 1)).toBe(true)
  })

  it('stops when there is no order for the session', () => {
    expect(shouldPoll({ state: 'missing' }, 1)).toBe(false)
  })

  it('gives up after the limit', () => {
    expect(shouldPoll(found('pending'), MAX_POLLS)).toBe(false)
    expect(shouldPoll({ state: 'error' }, MAX_POLLS)).toBe(false)
  })
})

describe('thankYouView', () => {
  it('shows the number of a paid order', () => {
    expect(thankYouView(found('paid'), 3)).toEqual({ kind: 'paid', number: 'PM-7K3QX9' })
  })

  it('treats a shipped order as paid', () => {
    expect(thankYouView(found('shipped'), 3).kind).toBe('paid')
  })

  it('shows the number while waiting for the payment', () => {
    expect(thankYouView(found('pending'), 3)).toEqual({ kind: 'waiting', number: 'PM-7K3QX9' })
  })

  it('switches to the slow message after the limit', () => {
    expect(thankYouView(found('pending'), MAX_POLLS)).toEqual({ kind: 'slow', number: 'PM-7K3QX9' })
    expect(thankYouView({ state: 'error' }, MAX_POLLS)).toEqual({ kind: 'slow', number: null })
  })

  it('shows a cancelled order', () => {
    expect(thankYouView(found('cancelled'), 3)).toEqual({ kind: 'cancelled', number: 'PM-7K3QX9' })
  })

  it('shows a refund separately from a cancellation', () => {
    expect(thankYouView(found('refunded'), 3)).toEqual({ kind: 'refunded', number: 'PM-7K3QX9' })
    expect(shouldPoll(found('refunded'), 3)).toBe(false)
  })

  it('keeps checking after a transient error', () => {
    expect(thankYouView({ state: 'error' }, 2)).toEqual({ kind: 'checking' })
  })

  it('shows the generic message when the order is unknown', () => {
    expect(thankYouView({ state: 'missing' }, 1)).toEqual({ kind: 'unknown' })
  })
})
