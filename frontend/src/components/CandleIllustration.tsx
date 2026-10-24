import type { CSSProperties } from 'react'
import styles from './CandleIllustration.module.css'

type CandleIllustrationProps = {
  /** Plaster colour (variant hex). */
  gips: string
  /** Accessible description; omit for a decorative illustration. */
  label?: string
  lit?: boolean
  className?: string
}

// Plaster pot from brand-sprite.svg; stands in for product photos until they exist.
export function CandleIllustration({ gips, label, lit = false, className }: CandleIllustrationProps) {
  const potStyle = { '--body': gips, '--rim': gips } as CSSProperties
  return (
    <svg
      className={className}
      viewBox="0 6 200 192"
      role={label ? 'img' : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
    >
      {lit && <circle className={styles.halo} cx="100" cy="40" r="36" />}
      <ellipse className={styles.shadow} cx="100" cy="182" rx="74" ry="7" />
      <use href="#pm-pot" className={styles.vessel} style={potStyle} />
      {lit && (
        <path
          className={styles.flame}
          d="M100 20 C114 34 115 48 100 60 C85 48 86 34 100 20Z"
          strokeWidth="5.5"
          strokeLinejoin="round"
        />
      )}
    </svg>
  )
}
