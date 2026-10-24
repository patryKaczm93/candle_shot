import { Button } from '../components/Button'
import { CandleIllustration } from '../components/CandleIllustration'
import styles from './NotFoundPage.module.css'

export function NotFoundPage() {
  return (
    <section className={`wrap ${styles.page}`}>
      <CandleIllustration gips="#FFFFFF" className={styles.candle} />
      <h1 className={`disp ${styles.title}`}>Tu jeszcze nic nie pachnie</h1>
      <p className={styles.text}>Tej strony nie ma albo dopiero powstaje.</p>
      <Button to="/" arrow>
        Na stronę główną
      </Button>
    </section>
  )
}
