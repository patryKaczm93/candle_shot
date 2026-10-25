import { useEffect, useRef, type CSSProperties } from 'react'
import { Link } from 'react-router'
import { fetchShipping } from '../api'
import {
  cartCorrections,
  cartLines,
  freeShippingMessage,
  freeShippingProgress,
  subtotalGrosze,
  type CartLine,
} from '../cart/summary'
import { useCart } from '../cart/useCart'
import { formatPrice } from '../format'
import { STOCK_LABELS } from '../productPage'
import { useApi } from '../useApi'
import { useProducts } from '../useProducts'
import { Button } from './Button'
import { IconButton } from './IconButton'
import { CloseIcon } from './icons'
import styles from './CartDrawer.module.css'

const FLAME = 'M100 20 C114 34 115 48 100 60 C85 48 86 34 100 20Z'

/** Cart drawer from the mockup: right-hand panel on desktop, bottom sheet on phones. */
export function CartDrawer() {
  const { isOpen, close } = useCart()
  const dialogRef = useRef<HTMLDialogElement>(null)

  // Native modal dialog: focus stays inside, Esc closes it, the page behind is inert.
  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) return
    if (isOpen && !dialog.open) dialog.showModal()
    if (!isOpen && dialog.open) dialog.close()
  }, [isOpen])

  return (
    <dialog
      ref={dialogRef}
      className={styles.drawer}
      aria-labelledby="cart-title"
      onClose={close}
      // The panel fills the dialog, so a click on the dialog itself is a click on the dimmed backdrop.
      onClick={(event) => event.target === event.currentTarget && close()}
    >
      {isOpen && <CartContents onClose={close} />}
    </dialog>
  )
}

function CartContents({ onClose }: { onClose: () => void }) {
  const { items, count, setQty, remove } = useCart()
  const products = useProducts()
  const shipping = useApi(fetchShipping, 'shipping')
  const catalogue = products.status === 'ready' ? products.data : null

  // Stock may have changed since the cart was filled: drop vanished variants, cap the last piece.
  useEffect(() => {
    if (!catalogue) return
    for (const fix of cartCorrections(items, catalogue)) setQty(fix.variantId, fix.qty)
  }, [catalogue, items, setQty])

  const lines = catalogue ? cartLines(items, catalogue) : []
  const subtotal = subtotalGrosze(lines)

  return (
    <div className={styles.panel}>
      <span className={styles.handle} aria-hidden="true" />
      <div className={styles.head}>
        <h2 id="cart-title" className={`disp ${styles.title}`}>
          Twój koszyk <span className={styles.count}>({count})</span>
        </h2>
        <IconButton label="Zamknij koszyk" onClick={onClose}>
          <CloseIcon />
        </IconButton>
      </div>

      {items.length === 0 || (catalogue && lines.length === 0) ? (
        <EmptyCart onClose={onClose} />
      ) : products.status === 'loading' ? (
        <p className={styles.status}>Wczytuję koszyk…</p>
      ) : products.status !== 'ready' ? (
        <div className={styles.status}>
          <p>Nie udało się wczytać koszyka. Sprawdź połączenie i spróbuj ponownie.</p>
          <Button variant="ghost" onClick={products.reload}>
            Spróbuj ponownie
          </Button>
        </div>
      ) : (
        <>
          {shipping.status === 'ready' && (
            <FreeShippingBar subtotal={subtotal} threshold={shipping.data.free_shipping_threshold_grosze} />
          )}

          <ul className={styles.items}>
            {lines.map((line, i) => (
              <CartItem
                key={line.variantId}
                line={line}
                index={i}
                onQty={(qty) => setQty(line.variantId, qty)}
                onRemove={() => remove(line.variantId)}
                onNavigate={onClose}
              />
            ))}
          </ul>

          <div className={styles.foot}>
            <div className={styles.sumRow}>
              <span>Suma częściowa</span>
              <span className={styles.sum}>{formatPrice(subtotal)}</span>
            </div>
            <div className={`${styles.sumRow} ${styles.muted}`}>
              <span>Dostawa</span>
              <span>w następnym kroku</span>
            </div>
            <Button to="/zamowienie" arrow className={styles.checkout} onClick={onClose}>
              Przejdź do zamówienia
            </Button>
            <Link to="/sklep" className={styles.continue} onClick={onClose}>
              Kontynuuj zakupy
            </Link>
          </div>
        </>
      )}
    </div>
  )
}

function FreeShippingBar({ subtotal, threshold }: { subtotal: number; threshold: number }) {
  const progress = freeShippingProgress(subtotal, threshold)
  return (
    <div className={styles.shipping}>
      <p className={styles.shippingMsg} aria-live="polite">
        {freeShippingMessage(progress)}
      </p>
      <div className={styles.track} aria-hidden="true">
        <div
          className={`${styles.bar} ${progress.reached ? styles.barFree : ''}`}
          style={{ transform: `scaleX(${progress.ratio})` }}
        />
      </div>
    </div>
  )
}

type CartItemProps = {
  line: CartLine
  index: number
  onQty: (qty: number) => void
  onRemove: () => void
  onNavigate: () => void
}

function CartItem({ line, index, onQty, onRemove, onNavigate }: CartItemProps) {
  const soldOut = line.availability === 'sold_out'
  const potStyle = { '--body': line.hex, '--rim': line.hex } as CSSProperties

  return (
    <li className={styles.item} style={{ '--i': index } as CSSProperties}>
      <span className={styles.thumb}>
        <svg viewBox="0 6 200 192" aria-hidden="true">
          <use href="#pm-pot-b" style={potStyle} />
          {!soldOut && <path className={styles.flame} d={FLAME} strokeWidth="7" strokeLinejoin="round" />}
        </svg>
      </span>

      <div className={styles.info}>
        <div className={styles.row}>
          <Link to={`/sklep/${line.slug}`} className={`disp ${styles.name}`} onClick={onNavigate}>
            {line.productName}
          </Link>
          <span className={styles.price}>{soldOut ? STOCK_LABELS.sold_out : formatPrice(line.lineTotalGrosze)}</span>
        </div>
        <span className={styles.variant}>Gips: {line.variantName}</span>
        {soldOut && <span className={styles.soldOut}>Ta partia się wypaliła. Usuń ją z koszyka.</span>}
        {line.availability === 'last' && <span className={styles.variant}>{STOCK_LABELS.last}</span>}

        <div className={`${styles.row} ${styles.actions}`}>
          <div role="group" aria-label={`Ilość: ${line.productName}`} className={styles.stepper}>
            <button
              type="button"
              aria-label="Zmniejsz ilość"
              disabled={soldOut || line.qty <= 1}
              onClick={() => onQty(line.qty - 1)}
            >
              −
            </button>
            <span aria-live="polite">{line.qty}</span>
            <button
              type="button"
              aria-label="Zwiększ ilość"
              disabled={line.qty >= line.max}
              onClick={() => onQty(line.qty + 1)}
            >
              +
            </button>
          </div>
          <button
            type="button"
            className={styles.linkBtn}
            aria-label={`Usuń ${line.productName}, gips ${line.variantName}`}
            onClick={onRemove}
          >
            Usuń
          </button>
        </div>
      </div>
    </li>
  )
}

function EmptyCart({ onClose }: { onClose: () => void }) {
  return (
    <div className={styles.empty}>
      <svg className={styles.emptyPot} viewBox="0 6 200 192" aria-hidden="true">
        <use href="#pm-pot" style={{ '--body': '#FFFFFF', '--rim': '#FFFFFF' } as CSSProperties} />
        <path className={styles.smoke} d="M100 55 C95 46 105 41 100 31" strokeWidth="3" strokeLinecap="round" />
      </svg>
      <h3 className={`disp ${styles.emptyTitle}`}>Tu jeszcze nic nie pachnie</h3>
      <p>Twój koszyk jest pusty. Zajrzyj do sklepu, na pewno coś się znajdzie.</p>
      <Button to="/sklep" className={styles.emptyBtn} onClick={onClose}>
        Przejdź do sklepu
      </Button>
    </div>
  )
}
