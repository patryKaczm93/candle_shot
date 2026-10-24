import type { ReactNode } from 'react'
import styles from './LegalPage.module.css'

type LegalPageProps = {
  title: string
  children: ReactNode
}

export function LegalPage({ title, children }: LegalPageProps) {
  return (
    <article className={`wrap ${styles.page}`}>
      <h1 className={`disp ${styles.title}`}>{title}</h1>
      {/* TODO(9.3): replace drafts with the final documents. */}
      <p className={styles.draft} role="note">
        Wersja robocza. Pola w nawiasach kwadratowych zostaną uzupełnione przed startem sklepu.
      </p>
      <div className={styles.body}>{children}</div>
    </article>
  )
}
