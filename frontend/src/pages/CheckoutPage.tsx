import { useEffect, useRef, useState, type CSSProperties, type FormEvent, type ReactNode } from 'react'
import { CheckoutError, fetchShipping, postCheckout } from '../api'
import { cartLines, shippingPriceGrosze, subtotalGrosze } from '../cart/summary'
import { useCart } from '../cart/useCart'
import {
  EMPTY_FORM,
  describeCheckoutFailure,
  firstInvalid,
  toCheckoutRequest,
  validate,
  type CheckoutForm,
  type FieldName,
  type FormErrors,
  type ShippingMethod,
} from '../checkout/form'
import { Button } from '../components/Button'
import { Field } from '../components/Field'
import { LockerPicker } from '../components/LockerPicker'
import { formatPrice } from '../format'
import { STOCK_LABELS } from '../productPage'
import { useApi } from '../useApi'
import { useProducts } from '../useProducts'
import styles from './CheckoutPage.module.css'

const FLAME = 'M100 20 C114 34 115 48 100 60 C85 48 86 34 100 20Z'

const SHIPPING_OPTIONS: { id: ShippingMethod; name: string; desc: string }[] = [
  { id: 'locker', name: 'Paczkomat InPost', desc: 'Odbiór 24/7, zwykle następnego dnia po wysyłce' },
  { id: 'courier', name: 'Kurier', desc: 'Dostawa pod wskazany adres' },
]

const fieldId = (name: FieldName) => `checkout-${name}`

export function CheckoutPage() {
  const { items, open: openCart } = useCart()
  const products = useProducts()
  const shipping = useApi(fetchShipping, 'shipping')

  const [form, setForm] = useState<CheckoutForm>(EMPTY_FORM)
  const [errors, setErrors] = useState<FormErrors>({})
  const [submitted, setSubmitted] = useState(false)
  const [busy, setBusy] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const [unavailable, setUnavailable] = useState<number[]>([])
  // State updates only after a render; the ref stops a double click / Enter + click at once.
  const inFlight = useRef(false)

  // Back from Stripe (page restored from the back/forward cache): let the customer try again.
  useEffect(() => {
    const onPageShow = (event: PageTransitionEvent) => {
      if (!event.persisted) return
      inFlight.current = false
      setBusy(false)
    }
    window.addEventListener('pageshow', onPageShow)
    return () => window.removeEventListener('pageshow', onPageShow)
  }, [])

  const catalogue = products.status === 'ready' ? products.data : null
  const lines = catalogue ? cartLines(items, catalogue) : []
  const subtotal = subtotalGrosze(lines)
  const shippingInfo = shipping.status === 'ready' ? shipping.data : null
  const shippingCost = shippingInfo ? shippingPriceGrosze(shippingInfo, form.method, subtotal) : null
  const total = shippingCost === null ? null : subtotal + shippingCost

  // After the first submit, errors follow what the customer types.
  const update = <K extends keyof CheckoutForm>(key: K, value: CheckoutForm[K]) => {
    const next = { ...form, [key]: value }
    setForm(next)
    if (submitted) setErrors(validate(next))
  }

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (inFlight.current) return
    const found = validate(form)
    setSubmitted(true)
    setErrors(found)
    setFormError(null)
    setUnavailable([])
    const first = firstInvalid(found)
    if (first) {
      document.getElementById(fieldId(first))?.focus()
      return
    }

    // Blocked until the response: every click would create a new order and reservation.
    inFlight.current = true
    setBusy(true)
    try {
      const { url } = await postCheckout(toCheckoutRequest(form, items))
      window.location.assign(url)
    } catch (error) {
      inFlight.current = false
      setBusy(false)
      const failure =
        error instanceof CheckoutError
          ? describeCheckoutFailure(error.status, error.detail)
          : describeCheckoutFailure(null, undefined)
      setErrors(failure.fields)
      setFormError(failure.message)
      setUnavailable(failure.unavailableVariantIds)
      const firstField = firstInvalid(failure.fields)
      if (firstField) document.getElementById(fieldId(firstField))?.focus()
      else document.getElementById('checkout-error')?.focus()
    }
  }

  const field = (name: FieldName) => ({
    id: fieldId(name),
    value: String(form[name]),
    error: errors[name],
    onChange: (event: { target: { value: string } }) => update(name, event.target.value),
  })

  if (items.length === 0) {
    return (
      <section className={`wrap ${styles.page}`}>
        <h1 className={`disp ${styles.title}`}>Zamówienie</h1>
        <div className={styles.empty}>
          <h2 className="disp">Tu jeszcze nic nie pachnie</h2>
          <p>Twój koszyk jest pusty, więc nie ma czego zamawiać.</p>
          <Button to="/sklep">Przejdź do sklepu</Button>
        </div>
      </section>
    )
  }

  return (
    <section className={`wrap ${styles.page}`}>
      <button type="button" className={styles.back} onClick={openCart}>
        ← Wróć do koszyka
      </button>
      <h1 className={`disp ${styles.title}`}>Zamówienie</h1>

      <div className={styles.grid}>
        <form className={styles.form} noValidate onSubmit={submit} aria-busy={busy}>
          {formError && (
            <div id="checkout-error" className={styles.alert} role="alert" tabIndex={-1}>
              <p>{formError}</p>
              {unavailable.length > 0 && (
                <Button variant="ghost" onClick={openCart}>
                  Otwórz koszyk
                </Button>
              )}
            </div>
          )}

          <section className={styles.section}>
            <h2 className={`disp ${styles.heading}`}>Kontakt</h2>
            <div className={styles.two}>
              <Field label="E-mail" type="email" autoComplete="email" placeholder="twoj@email.pl" {...field('email')} />
              <Field label="Telefon" type="tel" autoComplete="tel" placeholder="500 600 700" {...field('phone')} />
            </div>
            <p className={styles.note}>Na telefon przyjdzie SMS od InPost, na e-mail potwierdzenie zamówienia.</p>
          </section>

          <fieldset className={styles.fieldset}>
            <legend className={`disp ${styles.heading}`}>Dostawa</legend>
            <div className={styles.section}>
            {SHIPPING_OPTIONS.map((option) => {
              const price = shippingInfo ? shippingPriceGrosze(shippingInfo, option.id, subtotal) : null
              return (
                <label key={option.id} className={styles.option}>
                  <input
                    type="radio"
                    name="shipping"
                    value={option.id}
                    checked={form.method === option.id}
                    onChange={() => update('method', option.id)}
                  />
                  <span className={styles.dot} aria-hidden="true">
                    <i />
                  </span>
                  <span className={styles.optionText}>
                    <span className={styles.optionName}>{option.name}</span>
                    <span className={styles.optionDesc}>{option.desc}</span>
                  </span>
                  <span className={styles.optionPrice}>
                    {price === null ? '' : price === 0 ? 'Gratis' : formatPrice(price)}
                  </span>
                </label>
              )
            })}

            {form.method === 'locker' ? (
              <div className={styles.reveal}>
                <LockerPicker
                  id={fieldId('lockerId')}
                  value={form.lockerId}
                  onChange={(lockerId) => update('lockerId', lockerId)}
                  error={errors.lockerId}
                />
                <Field label="Imię i nazwisko" autoComplete="name" {...field('fullName')} />
              </div>
            ) : (
              <div className={styles.reveal}>
                <Field label="Imię i nazwisko" autoComplete="name" {...field('fullName')} />
                <Field label="Ulica i numer" autoComplete="street-address" {...field('addressLine')} />
                <div className={styles.two}>
                  <Field
                    label="Kod pocztowy"
                    inputMode="numeric"
                    placeholder="00-000"
                    autoComplete="postal-code"
                    maxLength={6}
                    {...field('postalCode')}
                  />
                  <Field label="Miasto" autoComplete="address-level2" {...field('city')} />
                </div>
              </div>
            )}

            <Checkbox checked={form.wantsInvoice} onChange={(checked) => update('wantsInvoice', checked)}>
              Chcę fakturę na firmę
            </Checkbox>
            {form.wantsInvoice && (
              <div className={`${styles.two} ${styles.reveal}`}>
                <Field label="NIP" inputMode="numeric" placeholder="526-000-12-46" {...field('nip')} />
                <Field label="Nazwa firmy" autoComplete="organization" {...field('invoiceName')} />
              </div>
            )}
            </div>
          </fieldset>

          <section className={styles.section}>
            <h2 className={`disp ${styles.heading}`}>Płatność</h2>
            <p className={styles.payInfo}>Zapłacisz BLIKIEM, Przelewy24 lub kartą na bezpiecznej stronie Stripe.</p>
            <p className={styles.note}>Płatność obsługuje Stripe. Nie przechowujemy danych twojej karty.</p>
          </section>

          <section className={`${styles.section} ${styles.final}`}>
            <div>
              <Checkbox
                id={fieldId('terms')}
                checked={form.terms}
                onChange={(checked) => update('terms', checked)}
                invalid={Boolean(errors.terms)}
                describedBy={errors.terms ? 'checkout-terms-error' : undefined}
              >
                Akceptuję{' '}
                <a href="/regulamin" target="_blank" rel="noopener">
                  regulamin
                </a>{' '}
                i{' '}
                <a href="/polityka-prywatnosci" target="_blank" rel="noopener">
                  politykę prywatności
                </a>
                .
              </Checkbox>
              {errors.terms && (
                <p id="checkout-terms-error" className={styles.termsError}>
                  {errors.terms}
                </p>
              )}
            </div>
            <div className={styles.payBar}>
              <Button type="submit" className={`${styles.pay} ${busy ? styles.busy : ''}`} disabled={busy}>
                {busy ? (
                  <>
                    <span className={styles.spinner} aria-hidden="true" />
                    Łączę z płatnością…
                  </>
                ) : (
                  `Zamawiam i płacę${total === null ? '' : ` · ${formatPrice(total)}`}`
                )}
              </Button>
              <p className={styles.payNote}>Po kliknięciu przejdziesz do bezpiecznej płatności Stripe.</p>
            </div>
          </section>
        </form>

        <OrderSummary
          loading={products.status === 'loading'}
          lines={lines}
          unavailable={unavailable}
          subtotal={subtotal}
          shippingName={SHIPPING_OPTIONS.find((o) => o.id === form.method)?.name ?? ''}
          shippingCost={shippingCost}
          total={total}
        />
      </div>
    </section>
  )
}

type CheckboxProps = {
  id?: string
  checked: boolean
  onChange: (checked: boolean) => void
  invalid?: boolean
  describedBy?: string
  children: ReactNode
}

function Checkbox({ id, checked, onChange, invalid, describedBy, children }: CheckboxProps) {
  return (
    <label className={styles.check}>
      <input
        id={id}
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        aria-invalid={invalid ? true : undefined}
        aria-describedby={describedBy}
      />
      <span className={styles.box} aria-hidden="true">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3.5">
          <path d="M5 12l5 5 9-10" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </span>
      <span>{children}</span>
    </label>
  )
}

type OrderSummaryProps = {
  loading: boolean
  lines: ReturnType<typeof cartLines>
  unavailable: number[]
  subtotal: number
  shippingName: string
  shippingCost: number | null
  total: number | null
}

function OrderSummary({ loading, lines, unavailable, subtotal, shippingName, shippingCost, total }: OrderSummaryProps) {
  const [open, setOpen] = useState(false)

  return (
    <aside className={styles.summary} aria-label="Podsumowanie zamówienia">
      <h2 className={`disp ${styles.heading}`}>Twoje zamówienie</h2>
      {/* Phones: the summary is collapsed above the form, as in Tel-Zamowienie. */}
      <button
        type="button"
        className={styles.toggle}
        aria-expanded={open}
        aria-controls="checkout-summary"
        onClick={() => setOpen((value) => !value)}
      >
        <span>{open ? 'Ukryj podsumowanie' : 'Pokaż podsumowanie'}</span>
        <span>{total === null ? '' : formatPrice(total)}</span>
      </button>

      <div id="checkout-summary" className={`${styles.summaryBody} ${open ? styles.summaryOpen : ''}`}>
        {loading && <p>Wczytuję koszyk…</p>}
        <ul className={styles.lines}>
          {lines.map((line) => {
            const problem = line.availability === 'sold_out' || unavailable.includes(line.variantId)
            return (
              <li key={line.variantId} className={styles.line}>
                <span className={styles.thumb}>
                  <svg viewBox="0 6 200 192" aria-hidden="true">
                    <use href="#pm-pot-b" style={{ '--body': line.hex, '--rim': line.hex } as CSSProperties} />
                    <path className={styles.flame} d={FLAME} strokeWidth="7" strokeLinejoin="round" />
                  </svg>
                  <span className={styles.qty} aria-label={`${line.qty} szt.`}>
                    {line.qty}
                  </span>
                </span>
                <span className={styles.lineText}>
                  <span className={styles.lineName}>{line.productName}</span>
                  <span className={styles.lineVariant}>Gips: {line.variantName}</span>
                  {problem && <span className={styles.lineProblem}>Niedostępna w tej ilości</span>}
                </span>
                <span className={styles.linePrice}>
                  {line.availability === 'sold_out' ? STOCK_LABELS.sold_out : formatPrice(line.lineTotalGrosze)}
                </span>
              </li>
            )
          })}
        </ul>

        <div className={styles.rows}>
          <div className={styles.row}>
            <span>Produkty</span>
            <span>{formatPrice(subtotal)}</span>
          </div>
          <div className={styles.row}>
            <span>Dostawa: {shippingName}</span>
            <span>{shippingCost === null ? '—' : shippingCost === 0 ? 'Gratis' : formatPrice(shippingCost)}</span>
          </div>
        </div>
        <div className={styles.totalRow}>
          <span>Razem</span>
          <span className={`disp ${styles.total}`}>{total === null ? '—' : formatPrice(total)}</span>
        </div>
        <p className={styles.vat}>
          Zawiera VAT. Wysyłka w [X] dni roboczych od zaksięgowania płatności. Kwotę ostatecznie potwierdzi strona
          płatności.
        </p>
      </div>
    </aside>
  )
}
