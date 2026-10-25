import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { Link } from 'react-router'
import styles from './Button.module.css'

type CommonProps = {
  variant?: 'main' | 'ghost'
  arrow?: boolean
  className?: string
  children: ReactNode
}

type ButtonProps = CommonProps &
  (
    | { to: string; href?: undefined; onClick?: () => void }
    | { href: string; to?: undefined }
    | ({ to?: undefined; href?: undefined } & ButtonHTMLAttributes<HTMLButtonElement>)
  )

/** Pill button from the mockup. `to` = router link, `href` = plain link (anchors, mailto), otherwise <button>. */
export function Button({ variant = 'main', arrow = false, className, children, ...rest }: ButtonProps) {
  const classes = [styles.btn, styles[variant], className].filter(Boolean).join(' ')
  const content = (
    <>
      {children}
      {arrow && (
        <span className={styles.arrow} aria-hidden="true">
          →
        </span>
      )}
    </>
  )

  if (rest.to !== undefined) {
    return (
      <Link to={rest.to} className={classes} onClick={rest.onClick}>
        {content}
      </Link>
    )
  }

  if (rest.href !== undefined) {
    return (
      <a href={rest.href} className={classes}>
        {content}
      </a>
    )
  }

  const { to: _to, href: _href, type = 'button', ...buttonProps } = rest
  return (
    <button type={type} className={classes} {...buttonProps}>
      {content}
    </button>
  )
}
