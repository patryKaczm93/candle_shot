import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { Link } from 'react-router'
import { Badge } from './Badge'
import styles from './IconButton.module.css'

type CommonProps = {
  /** Required: the button shows only an icon. */
  label: string
  count?: number
  children: ReactNode
}

type IconButtonProps = CommonProps &
  ({ to: string } | ({ to?: undefined } & ButtonHTMLAttributes<HTMLButtonElement>))

export function IconButton({ label, count = 0, children, ...rest }: IconButtonProps) {
  const content = (
    <>
      {children}
      {count > 0 && (
        <Badge count className={styles.badge}>
          {count}
        </Badge>
      )}
    </>
  )

  if (rest.to !== undefined) {
    return (
      <Link to={rest.to} aria-label={label} className={styles.iconBtn}>
        {content}
      </Link>
    )
  }

  const { to: _to, type = 'button', ...buttonProps } = rest
  return (
    <button type={type} aria-label={label} className={styles.iconBtn} {...buttonProps}>
      {content}
    </button>
  )
}
