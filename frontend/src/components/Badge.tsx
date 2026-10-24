import type { ReactNode } from 'react'
import styles from './Badge.module.css'

type BadgeProps = {
  children: ReactNode
  /** Small round counter (cart) instead of a text label (Bestseller, Nowość…). */
  count?: boolean
  className?: string
}

export function Badge({ children, count = false, className }: BadgeProps) {
  const classes = [styles.badge, count ? styles.count : styles.label, className].filter(Boolean).join(' ')
  return <span className={classes}>{children}</span>
}
