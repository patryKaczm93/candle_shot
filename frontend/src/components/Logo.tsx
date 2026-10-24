import { Link } from 'react-router'
import logoMarkSvg from '../assets/logo-mark.svg?raw'
import styles from './Logo.module.css'

const FLAME = /<path d="M100 20 [^>]*\/>/

// Inner shapes of logo-mark.svg with the flame wrapped in its own group, so it can flicker.
const markShapes = logoMarkSvg
  .replace(/^[\s\S]*?<svg[^>]*>/, '')
  .replace(/<\/svg>\s*$/, '')
  .replace(/<!--[\s\S]*?-->/g, '')
  .replace(FLAME, (flame) => `<g class="${styles.flame}">${flame}</g>`)

type LogoProps = {
  variant?: 'header' | 'footer'
}

export function Logo({ variant = 'header' }: LogoProps) {
  const content = (
    <>
      <svg
        className={styles.mark}
        viewBox="0 12 200 168"
        aria-hidden="true"
        dangerouslySetInnerHTML={{ __html: markShapes }}
      />
      <span className={styles.wordmark}>
        Pachnie
        <br />
        miło
      </span>
    </>
  )

  if (variant === 'footer') {
    return (
      <div role="img" aria-label="Pachnie miło" className={`${styles.logo} ${styles.footer}`}>
        {content}
      </div>
    )
  }

  return (
    <Link to="/" aria-label="Pachnie miło, strona główna" className={`${styles.logo} ${styles.header}`}>
      {content}
    </Link>
  )
}
