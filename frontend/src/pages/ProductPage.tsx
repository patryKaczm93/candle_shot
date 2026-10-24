import { useState, type CSSProperties } from 'react'
import { Link, useParams } from 'react-router'
import { fetchProduct, fetchShipping, type Product, type ProductDetail, type ShippingInfo } from '../api'
import { Badge } from '../components/Badge'
import { Button } from '../components/Button'
import { cardColour, isSoldOut } from '../catalog'
import { formatPrice } from '../format'
import {
  MAX_QTY,
  STOCK_LABELS,
  addLabel,
  canAdd,
  clampQty,
  initialVariant,
  maxQty,
  qtyLabel,
} from '../productPage'
import { useApi } from '../useApi'
import { useProducts } from '../useProducts'
import { NotFoundPage } from './NotFoundPage'
import styles from './ProductPage.module.css'

const VIEWS = [
  { label: 'Front', camera: 'none' },
  { label: 'Z góry', camera: 'translateY(18%) scale(1.35)' },
  { label: 'W pokoju', camera: 'scale(0.7)' },
  { label: 'Detal gipsu', camera: 'translate(14%, -26%) scale(2.1)' },
]

export function ProductPage() {
  const { slug = '' } = useParams()
  const product = useApi((signal) => fetchProduct(slug, signal), `product:${slug}`)

  if (product.status === 'not-found') return <NotFoundPage />
  if (product.status === 'loading') {
    return (
      <p className={`wrap ${styles.status}`} role="status">
        Wyciągamy świeczkę z formy…
      </p>
    )
  }
  if (product.status === 'error') {
    return (
      <div className={`wrap ${styles.status}`} role="alert">
        <p>Nie udało się wczytać świeczki. Sprawdź połączenie i spróbuj jeszcze raz.</p>
        <Button onClick={product.reload}>Spróbuj ponownie</Button>
      </div>
    )
  }

  // key: a new product starts with fresh colour and quantity.
  return <ProductView key={product.data.slug} product={product.data} />
}

function ProductView({ product }: { product: ProductDetail }) {
  const shipping = useApi(fetchShipping, 'shipping')
  const [variantId, setVariantId] = useState(() => initialVariant(product.variants)?.id)
  const [qty, setQty] = useState(1)
  const [view, setView] = useState(0)

  const variant = product.variants.find((v) => v.id === variantId)
  const availability = variant?.availability ?? 'sold_out'
  const soldOut = isSoldOut(product) || product.variants.length === 0
  const max = maxQty(availability)
  const gips = variant?.hex ?? '#FFFFFF'
  const badge = soldOut ? 'Wyprzedana' : product.badge
  const shippingInfo = shipping.status === 'ready' ? shipping.data : null

  const pickVariant = (id: number) => {
    setVariantId(id)
    const next = product.variants.find((v) => v.id === id)
    if (next) setQty((current) => clampQty(current, next.availability))
  }

  const addToCart = () => {
    // TODO(4.1): add { variantId, qty } to the cart.
  }

  return (
    <>
      <section className={`wrap ${styles.page}`}>
        <nav aria-label="Okruszki" className={styles.breadcrumbs}>
          <Link to="/">Strona główna</Link> / <Link to="/sklep">Sklep</Link> / {product.name}
        </nav>

        <div className={styles.grid}>
          <div className={styles.gallery}>
            <div className={styles.picture}>
              {badge && <Badge className={styles.badge}>{badge}</Badge>}
              <svg
                className={styles.candle}
                viewBox="0 6 200 192"
                role="img"
                aria-label={`Świeczka w gipsie w kolorze ${variant?.name ?? ''}, widok: ${VIEWS[view].label}. Miejsce na zdjęcie.`}
              >
                <g className={styles.camera} style={{ transform: VIEWS[view].camera }}>
                  <ellipse className={styles.shadow} cx="100" cy="182" rx="74" ry="7" />
                  <use href="#pm-pot" className={styles.vessel} style={{ '--body': gips, '--rim': gips } as CSSProperties} />
                  {!soldOut && (
                    <path
                      className={styles.flame}
                      d="M100 20 C114 34 115 48 100 60 C85 48 86 34 100 20Z"
                      strokeWidth="5.5"
                      strokeLinejoin="round"
                    />
                  )}
                </g>
              </svg>
              <span className={styles.viewLabel}>
                {VIEWS[view].label}, {view + 1} z {VIEWS.length}
              </span>
            </div>
            <div className={styles.thumbs}>
              {VIEWS.map((v, i) => (
                <button
                  key={v.label}
                  type="button"
                  className={styles.thumb}
                  aria-label={`Pokaż widok: ${v.label}`}
                  aria-pressed={view === i}
                  onClick={() => setView(i)}
                >
                  {v.label}
                </button>
              ))}
            </div>
          </div>

          <div className={styles.details}>
            <div>
              <h1 className={`disp ${styles.name}`}>{product.name}</h1>
              {product.tagline && <p className={styles.tagline}>{product.tagline}</p>}
            </div>

            <div className={styles.priceRow}>
              <span className={`disp ${styles.price}`}>{formatPrice(product.price_grosze)}</span>
              <span className={styles.priceNote}>z VAT{product.weight_g ? ` · ${product.weight_g} g` : ''}</span>
            </div>

            {product.variants.length > 0 && (
              <fieldset className={styles.colours}>
                <legend>
                  Kolor gipsu: <span className={styles.colourName}>{variant?.name}</span>
                </legend>
                <div className={styles.swatches}>
                  {product.variants.map((v) => (
                    <button
                      key={v.id}
                      type="button"
                      className={styles.swatch}
                      style={{ background: v.hex }}
                      aria-label={`Gips ${v.name}${v.availability === 'sold_out' ? ', wyprzedany' : ''}`}
                      aria-pressed={v.id === variantId}
                      data-sold-out={v.availability === 'sold_out' || undefined}
                      onClick={() => pickVariant(v.id)}
                    />
                  ))}
                </div>
              </fieldset>
            )}

            {soldOut ? (
              <div className={styles.soldOut}>
                <strong>Ta partia się wypaliła</strong>
                <span>Następne wylewanie w [termin].</span>
              </div>
            ) : (
              <div className={styles.buy}>
                <div className={styles.buyRow}>
                  <div role="group" aria-label="Ilość" className={styles.stepper}>
                    <button
                      type="button"
                      aria-label="Zmniejsz ilość"
                      disabled={qty <= 1 || max === 0}
                      onClick={() => setQty((q) => clampQty(q - 1, availability))}
                    >
                      −
                    </button>
                    <span aria-live="polite">{qty}</span>
                    <button
                      type="button"
                      aria-label="Zwiększ ilość"
                      disabled={qty >= max}
                      onClick={() => setQty((q) => clampQty(q + 1, availability))}
                    >
                      +
                    </button>
                  </div>
                  <AddButton className={styles.addDesktop} qty={qty} disabled={!canAdd(availability)} onClick={addToCart} />
                </div>
                {qty >= MAX_QTY && (
                  <span className={styles.hint}>
                    Maksymalnie 10 sztuk w jednym zamówieniu. Większe zamówienia przyjmujemy mailowo.
                  </span>
                )}
                {availability === 'sold_out' && (
                  <span className={styles.hint}>Ten kolor jest wyprzedany. Wybierz inny kolor gipsu.</span>
                )}
              </div>
            )}

            <ul className={styles.perks}>
              <li>
                <svg viewBox="0 0 24 24" aria-hidden="true" className={styles.stockIcon} data-availability={availability}>
                  <path d={availability === 'sold_out' ? 'M6 6l12 12M18 6L6 18' : 'M5 12l5 5 9-10'} />
                </svg>
                <span>
                  <strong className={styles.stockLabel} data-availability={availability}>
                    {STOCK_LABELS[availability]}
                  </strong>{' '}
                  · {availability === 'sold_out' ? 'kolejna partia w [termin]' : 'wysyłka w [X] dni roboczych'}
                </span>
              </li>
              <li>
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <rect x="3" y="7" width="13" height="10" rx="1" />
                  <path d="M16 10h3l2 3v4h-5" />
                  <circle cx="7" cy="18" r="1.5" />
                  <circle cx="18" cy="18" r="1.5" />
                </svg>
                <span>
                  Paczkomat InPost lub kurier
                  {shippingInfo && `, darmowa od ${formatPrice(shippingInfo.free_shipping_threshold_grosze)}`}
                </span>
              </li>
              <li>
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M4 12a8 8 0 1 0 3-6.2" />
                  <path d="M4 4v4h4" />
                </svg>
                <span>14 dni na zwrot</span>
              </li>
              <li>
                <svg viewBox="0 6 200 174" aria-hidden="true" className={styles.markIcon}>
                  <use href="#pm-mark-b" />
                </svg>
                <span>
                  Chcesz własny kształt? <Link to="/#na-zamowienie">Zrobimy świeczkę na zamówienie</Link>
                </span>
              </li>
            </ul>

            <Accordion items={accordionItems(product, shippingInfo)} />

            {/* TODO(9.3): CLP pictograms and producer details required for scented candles. */}
            <div className={styles.clp}>
              [Piktogramy i ostrzeżenia z etykiety CLP oraz dane producenta, wymagane przy świecach zapachowych]
            </div>
          </div>
        </div>
      </section>

      {!soldOut && (
        <div className={styles.mobileBar}>
          <span className={styles.mobileBarPrice}>
            <span>{qtyLabel(qty)}</span>
            <span className="disp">{formatPrice(product.price_grosze)}</span>
          </span>
          <AddButton qty={qty} disabled={!canAdd(availability)} onClick={addToCart} />
        </div>
      )}

      <Related currentSlug={product.slug} />
    </>
  )
}

type AddButtonProps = { qty: number; disabled: boolean; onClick: () => void; className?: string }

function AddButton({ qty, disabled, onClick, className }: AddButtonProps) {
  return (
    <Button className={`${styles.add} ${className ?? ''}`} disabled={disabled} onClick={onClick}>
      {addLabel(qty)}
    </Button>
  )
}

function accordionItems(product: ProductDetail, shipping: ShippingInfo | null) {
  const price = (id: 'locker' | 'courier') => {
    const method = shipping?.methods.find((m) => m.id === id)
    return method ? formatPrice(method.price_grosze) : '[cena]'
  }
  const freeFrom = shipping ? formatPrice(shipping.free_shipping_threshold_grosze) : '[kwota]'

  return [
    { title: 'O zapachu', body: product.description },
    {
      title: 'Jak palić bezpiecznie',
      body:
        'Za pierwszym razem pal, aż wosk roztopi się na całej powierzchni (ok. [X] h).\n' +
        'Przycinaj knot do ok. 5 mm przed każdym zapaleniem.\n' +
        'Nie zostawiaj płonącej świeczki bez nadzoru. Stawiaj ją na stabilnej, niepalnej powierzchni.',
    },
    {
      title: 'Dostawa i zwroty',
      body:
        `Paczkomat InPost: ${price('locker')}. Kurier: ${price('courier')}. Darmowa dostawa od ${freeFrom}.\n` +
        'Masz 14 dni na odstąpienie od umowy bez podania przyczyny.',
    },
    {
      title: 'Własny kształt na zamówienie',
      body:
        'Możemy zaprojektować naczynie od zera, według Twojego pomysłu. Do ceny świeczek doliczamy wtedy ' +
        'jednorazowo koszt projektu 3D i formy silikonowej do odlewów. Wykonujemy też same formy silikonowe.',
    },
  ].filter((item) => item.body)
}

function Accordion({ items }: { items: { title: string; body: string }[] }) {
  const [open, setOpen] = useState(0)

  return (
    <div className={styles.accordion}>
      {items.map((item, i) => {
        const isOpen = open === i
        const panelId = `acc-panel-${i}`
        return (
          <div key={item.title} className={styles.accItem}>
            <button
              type="button"
              className={styles.accButton}
              aria-expanded={isOpen}
              aria-controls={panelId}
              onClick={() => setOpen(isOpen ? -1 : i)}
            >
              <span>{item.title}</span>
              <svg viewBox="0 0 24 24" aria-hidden="true" className={styles.chevron}>
                <path d="M6 9l6 6 6-6" />
              </svg>
            </button>
            {isOpen && (
              <div id={panelId} className={styles.accPanel}>
                {item.body}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

function Related({ currentSlug }: { currentSlug: string }) {
  const products = useProducts()
  if (products.status !== 'ready') return null

  const related = products.data.filter((p) => p.slug !== currentSlug).slice(0, 3)
  if (related.length === 0) return null

  return (
    <section className={styles.related}>
      <div className="wrap">
        <h2 className={`disp ${styles.relatedTitle}`}>Może ci się spodobać</h2>
        <div className={styles.relatedGrid}>
          {related.map((p) => (
            <RelatedCard key={p.slug} product={p} />
          ))}
        </div>
      </div>
    </section>
  )
}

function RelatedCard({ product }: { product: Product }) {
  const gips = cardColour(product)
  return (
    <Link to={`/sklep/${product.slug}`} className={styles.relatedCard}>
      <span className={styles.relatedPicture}>
        <svg viewBox="0 6 200 192" aria-hidden="true">
          <use href="#pm-pot" style={{ '--body': gips, '--rim': gips } as CSSProperties} />
        </svg>
      </span>
      <span className={styles.relatedBody}>
        <span className={`disp ${styles.relatedName}`}>{product.name}</span>
        {product.tagline && <span className={styles.relatedTagline}>{product.tagline}</span>}
        <span className={styles.relatedPrice}>{formatPrice(product.price_grosze)}</span>
      </span>
    </Link>
  )
}
