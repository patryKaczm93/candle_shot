import { useEffect, useState, type ReactNode } from 'react'
import { useSearchParams } from 'react-router'
import { ApiError, fetchOrderBySession } from '../api'
import { useCart } from '../cart/useCart'
import { POLL_INTERVAL_MS, shouldPoll, thankYouView, type OrderLookup } from '../checkout/orderStatus'
import { mailto } from '../shop'
import { Button } from '../components/Button'
import { CandleIllustration } from '../components/CandleIllustration'
import styles from './OrderResultPage.module.css'

type ResultProps = {
  lit: boolean
  title: string
  children: ReactNode
}

function Result({ lit, title, children }: ResultProps) {
  return (
    <section className={`wrap ${styles.page}`}>
      <div className={styles.card}>
        <CandleIllustration gips="#FFFFFF" lit={lit} className={styles.candle} />
        <h1 className={`disp ${styles.title}`}>{title}</h1>
        {children}
      </div>
    </section>
  )
}

/**
 * Asks the backend for the order every 2 s until the webhook marks it paid or cancelled.
 * The page never changes the order; the redirect from Stripe proves nothing about the payment.
 */
function useOrderStatus(sessionId: string | null): { lookup: OrderLookup; polls: number } {
  // Tagged with its session, so a result for a previous session_id is never shown.
  const [result, setResult] = useState<{ sessionId: string; lookup: OrderLookup; polls: number } | null>(null)

  useEffect(() => {
    if (!sessionId) return
    const controller = new AbortController()
    let timer: number | undefined
    let count = 0

    const poll = async () => {
      let next: OrderLookup
      try {
        next = { state: 'found', order: await fetchOrderBySession(sessionId, controller.signal) }
      } catch (error) {
        next = error instanceof ApiError && error.status === 404 ? { state: 'missing' } : { state: 'error' }
      }
      // Unmounted while waiting: no state updates and no new timer after cleanup.
      if (controller.signal.aborted) return
      count += 1
      setResult({ sessionId, lookup: next, polls: count })
      if (shouldPoll(next, count)) timer = window.setTimeout(poll, POLL_INTERVAL_MS)
    }

    void poll()
    return () => {
      controller.abort()
      window.clearTimeout(timer)
    }
  }, [sessionId])

  if (result && result.sessionId === sessionId) return { lookup: result.lookup, polls: result.polls }
  return { lookup: { state: 'loading' }, polls: 0 }
}

function OrderNumber({ number }: { number: string }) {
  return (
    <p className={styles.number}>
      Numer zamówienia: <strong>{number}</strong>
    </p>
  )
}

/** Return from Stripe after payment. The status shown here comes only from the backend. */
export function ThankYouPage() {
  const [searchParams] = useSearchParams()
  const { clear } = useCart()
  const sessionId = searchParams.get('session_id')
  const { lookup, polls } = useOrderStatus(sessionId)
  const view = sessionId ? thankYouView(lookup, polls) : ({ kind: 'unknown' } as const)

  // The backend knows this order, so it was placed; a new visit to the shop starts with an empty cart.
  const orderFound = lookup.state === 'found'
  useEffect(() => {
    if (orderFound) clear()
  }, [orderFound, clear])

  if (view.kind === 'cancelled') {
    return (
      <Result lit={false} title="Płatność nie doszła do skutku">
        <OrderNumber number={view.number} />
        <p className={styles.text}>
          Zamówienie zostało anulowane. Jeśli mimo to pieniądze zostały pobrane, zwrócimy je. W razie pytań{' '}
          <a href={mailto(`Zamówienie ${view.number}`)}>napisz do nas</a>.
        </p>
        <Button to="/sklep" arrow>
          Wróć do sklepu
        </Button>
      </Result>
    )
  }

  if (view.kind === 'refunded') {
    return (
      <Result lit={false} title="Zamówienie zostało zwrócone">
        <OrderNumber number={view.number} />
        <p className={styles.text}>
          Pieniądze za to zamówienie zostały zwrócone. W razie pytań{' '}
          <a href={mailto(`Zamówienie ${view.number}`)}>napisz do nas</a>.
        </p>
        <Button to="/sklep" arrow>
          Wróć do sklepu
        </Button>
      </Result>
    )
  }

  return (
    <Result lit title="Dziękujemy za zamówienie!">
      <div role="status" className={styles.status}>
        {view.kind === 'paid' && (
          <>
            <OrderNumber number={view.number} />
            <p className={styles.text}>
              Płatność przyjęta. Potwierdzenie wysłaliśmy e-mailem. Damy znać, gdy paczka wyruszy.
            </p>
          </>
        )}
        {view.kind === 'waiting' && (
          <>
            <OrderNumber number={view.number} />
            <p className={styles.text}>Czekamy na potwierdzenie płatności…</p>
          </>
        )}
        {view.kind === 'checking' && <p className={styles.text}>Sprawdzamy status zamówienia…</p>}
        {view.kind === 'slow' && (
          <>
            {view.number && <OrderNumber number={view.number} />}
            <p className={styles.text}>
              Potwierdzenie płatności jeszcze do nas nie dotarło. Przy przelewie może to potrwać dłużej. Gdy
              tylko przyjdzie, wyślemy e-mail z potwierdzeniem.
            </p>
          </>
        )}
        {view.kind === 'unknown' && (
          <p className={styles.text}>
            Gdy tylko płatność zostanie potwierdzona, wyślemy e-mail z numerem zamówienia.
          </p>
        )}
      </div>
      <Button to="/sklep" variant="ghost">
        Wróć do sklepu
      </Button>
    </Result>
  )
}

/** Cancel on the Stripe page: the cart stays, the customer can try again. */
export function OrderCancelledPage() {
  return (
    <Result lit={false} title="Płatność przerwana">
      <p className={styles.text}>
        Nic nie zostało pobrane. Twój koszyk czeka, możesz wrócić do zamówienia i spróbować jeszcze raz.
      </p>
      <Button to="/zamowienie" arrow>
        Wróć do zamówienia
      </Button>
    </Result>
  )
}
