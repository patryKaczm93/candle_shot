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
  ({ to: string } | ({ to?: undefined } & ButtonHTMLAttributes<HTMLButtonElement>))

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
      <Link to={rest.to} className={classes}>
        {content}
      </Link>
    )
  }

  const { to: _to, type = 'button', ...buttonProps } = rest
  return (
    <button type={type} className={classes} {...buttonProps}>
      {content}
    </button>
  )
}
