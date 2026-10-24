import type { CSSProperties } from 'react'
import { Link } from 'react-router'
import type { Product } from '../api'
import { cardColour, isSoldOut } from '../catalog'
import { formatPrice } from '../format'
import { Badge } from './Badge'
import styles from './ProductCard.module.css'

type ProductCardProps = {
  product: Product
  /** Position in the grid, for the staggered entrance. */
  index?: number
}

export function ProductCard({ product, index = 0 }: ProductCardProps) {
  const soldOut = isSoldOut(product)
  const badge = soldOut ? 'Wyprzedana' : product.badge
  const gips = cardColour(product)

  return (
    <Link
      to={`/sklep/${product.slug}`}
      className={styles.card}
      style={{ '--delay': `${index * 70}ms` } as CSSProperties}
    >
      <div className={styles.picture}>
        {badge && <Badge className={styles.badge}>{badge}</Badge>}
        <svg className={styles.candle} viewBox="0 6 200 192" role="img" aria-label={`${product.name}, miejsce na zdjęcie`}>
          <ellipse className={styles.shadow} cx="100" cy="182" rx="74" ry="7" />
          <use href="#pm-pot" style={{ '--body': gips, '--rim': gips } as CSSProperties} />
          <path className={styles.smoke} d="M100 55 C95 46 105 41 100 31" />
          {!soldOut && (
            <path
              className={styles.flame}
              d="M100 20 C114 34 115 48 100 60 C85 48 86 34 100 20Z"
              strokeWidth="5.5"
              strokeLinejoin="round"
            />
          )}
        </svg>
        <span className={styles.quick} aria-hidden="true">
          Zobacz →
        </span>
      </div>
      <div className={styles.body}>
        <span className={`disp ${styles.name}`}>{product.name}</span>
        {product.tagline && <span className={styles.tagline}>{product.tagline}</span>}
        <div className={styles.meta}>
          <span className={styles.price}>{formatPrice(product.price_grosze)}</span>
          {product.weight_g && <span className={styles.weight}>{product.weight_g} g</span>}
        </div>
      </div>
    </Link>
  )
}
