import { useEffect, type ReactNode } from 'react'
import { useSearchParams } from 'react-router'
import { useCart } from '../cart/useCart'
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
 * Return from Stripe after payment. Shows nothing about the payment itself: the order becomes
 * `paid` only in the webhook; the order number and status come in 6.4.
 */
export function ThankYouPage() {
  const [searchParams] = useSearchParams()
  const { clear } = useCart()
  const fromStripe = searchParams.has('session_id')

  // The order is placed; a new visit to the shop starts with an empty cart.
  useEffect(() => {
    if (fromStripe) clear()
  }, [fromStripe, clear])

  return (
    <Result lit title="Dziękujemy za zamówienie!">
      <p className={styles.text}>
        Gdy tylko płatność zostanie potwierdzona, wyślemy e-mail z numerem zamówienia. Zwykle trwa to kilka
        sekund, przy przelewie może potrwać dłużej.
      </p>
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
