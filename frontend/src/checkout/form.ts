import type { CheckoutRequest } from '../api'
import type { Cart } from '../cart/cart'

// Same rules as the backend (app/schemas.py). The backend validates again; this only gives
// faster feedback next to the fields.

export type ShippingMethod = 'locker' | 'courier'

export type CheckoutForm = {
  email: string
  phone: string
  fullName: string
  method: ShippingMethod
  lockerId: string
  addressLine: string
  postalCode: string
  city: string
  wantsInvoice: boolean
  nip: string
  invoiceName: string
  terms: boolean
}

export type FieldName = Exclude<keyof CheckoutForm, 'method' | 'wantsInvoice'>
export type FormErrors = Partial<Record<FieldName, string>>

export const EMPTY_FORM: CheckoutForm = {
  email: '',
  phone: '',
  fullName: '',
  method: 'locker',
  lockerId: '',
  addressLine: '',
  postalCode: '',
  city: '',
  wantsInvoice: false,
  nip: '',
  invoiceName: '',
  terms: false,
}

export const MESSAGES: Record<FieldName, string> = {
  email: 'Wpisz adres e-mail, np. anna@example.com',
  phone: 'Wpisz numer telefonu, np. 500 600 700',
  fullName: 'Wpisz imię i nazwisko',
  lockerId: 'Wybierz Paczkomat',
  addressLine: 'Wpisz ulicę i numer',
  postalCode: 'Kod pocztowy w formacie 00-000',
  city: 'Wpisz miasto',
  nip: 'Nieprawidłowy NIP',
  invoiceName: 'Wpisz nazwę firmy',
  terms: 'Zaznacz zgodę, żeby złożyć zamówienie.',
}

/** Order of fields on the page: the first invalid one gets focus. */
export const FIELD_ORDER: FieldName[] = [
  'email',
  'phone',
  'lockerId',
  'fullName',
  'addressLine',
  'postalCode',
  'city',
  'nip',
  'invoiceName',
  'terms',
]

const EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s]+$/
const PHONE = /^\+?[0-9]{9,15}$/
const LOCKER = /^[A-Z0-9-]{4,20}$/
const POSTAL_CODE = /^[0-9]{2}-[0-9]{3}$/
const NIP_WEIGHTS = [6, 5, 7, 2, 3, 4, 5, 6, 7]

export function normalizePhone(phone: string): string {
  return phone.replace(/[\s()-]/g, '')
}

export function normalizeNip(nip: string): string {
  return nip.replace(/[\s-]/g, '').toUpperCase().replace(/^PL/, '')
}

/** Polish NIP: 10 digits, the last one is a weighted checksum (mod 11, never 10). */
export function isValidNip(nip: string): boolean {
  if (!/^[0-9]{10}$/.test(nip)) return false
  const checksum = NIP_WEIGHTS.reduce((sum, weight, i) => sum + weight * Number(nip[i]), 0) % 11
  return checksum !== 10 && checksum === Number(nip[9])
}

function between(value: string, min: number, max: number): boolean {
  const length = value.trim().length
  return length >= min && length <= max
}

export function validate(form: CheckoutForm): FormErrors {
  const errors: FormErrors = {}
  const email = form.email.trim()
  if (email.length > 254 || !EMAIL.test(email)) errors.email = MESSAGES.email
  if (!PHONE.test(normalizePhone(form.phone))) errors.phone = MESSAGES.phone
  if (!between(form.fullName, 2, 200)) errors.fullName = MESSAGES.fullName

  if (form.method === 'locker') {
    if (!LOCKER.test(form.lockerId.trim().toUpperCase())) errors.lockerId = MESSAGES.lockerId
  } else {
    if (!between(form.addressLine, 3, 200)) errors.addressLine = MESSAGES.addressLine
    if (!POSTAL_CODE.test(form.postalCode.trim())) errors.postalCode = MESSAGES.postalCode
    if (!between(form.city, 2, 100)) errors.city = MESSAGES.city
  }

  if (form.wantsInvoice) {
    if (!isValidNip(normalizeNip(form.nip))) errors.nip = MESSAGES.nip
    if (!between(form.invoiceName, 2, 200)) errors.invoiceName = MESSAGES.invoiceName
  }

  if (!form.terms) errors.terms = MESSAGES.terms
  return errors
}

export function firstInvalid(errors: FormErrors): FieldName | undefined {
  return FIELD_ORDER.find((field) => errors[field])
}

/** Request body: only variant ids and quantities, never prices. */
export function toCheckoutRequest(form: CheckoutForm, cart: Cart): CheckoutRequest {
  return {
    email: form.email.trim(),
    phone: form.phone.trim(),
    full_name: form.fullName.trim(),
    shipping:
      form.method === 'locker'
        ? { method: 'locker', locker_id: form.lockerId.trim() }
        : {
            method: 'courier',
            address_line: form.addressLine.trim(),
            postal_code: form.postalCode.trim(),
            city: form.city.trim(),
          },
    invoice: form.wantsInvoice ? { nip: form.nip.trim(), name: form.invoiceName.trim() } : null,
    terms_accepted: form.terms,
    items: cart.map(({ variantId, qty }) => ({ variant_id: variantId, qty })),
  }
}

// Last element of a FastAPI/Pydantic error `loc`, e.g. ["body", "shipping", "courier", "postal_code"].
const API_FIELDS: Record<string, FieldName> = {
  email: 'email',
  phone: 'phone',
  full_name: 'fullName',
  locker_id: 'lockerId',
  address_line: 'addressLine',
  postal_code: 'postalCode',
  city: 'city',
  nip: 'nip',
  terms_accepted: 'terms',
}

export type ApiValidationError = { loc: (string | number)[]; msg: string }

/** 422 from the API → messages next to the fields; anything else is a general error. */
export function apiErrorsToFields(errors: ApiValidationError[]): { fields: FormErrors; general: boolean } {
  const fields: FormErrors = {}
  let general = false
  for (const error of errors) {
    const last = String(error.loc[error.loc.length - 1])
    const field = error.loc.includes('invoice') && last === 'name' ? 'invoiceName' : API_FIELDS[last]
    if (field) fields[field] = MESSAGES[field]
    else general = true
  }
  return { fields, general }
}

export type CheckoutFailure = {
  fields: FormErrors
  /** Shown above the form; null when the field messages say it all. */
  message: string | null
  unavailableVariantIds: number[]
}

const GENERIC_ERROR = 'Nie udało się złożyć zamówienia. Spróbuj ponownie za chwilę.'
const CART_ERROR = 'Coś jest nie tak z koszykiem. Otwórz koszyk, sprawdź produkty i spróbuj ponownie.'

/** Turns a failed POST /api/checkout (status + `detail`) into messages for the form. */
export function describeCheckoutFailure(status: number | null, detail: unknown): CheckoutFailure {
  const none = { fields: {}, message: null, unavailableVariantIds: [] }
  if (status === null) {
    return {
      ...none,
      message:
        'Nie udało się połączyć ze sklepem. Sprawdź internet i spróbuj ponownie. Jeśli zamówienie zdążyło powstać, ' +
        'a nie zapłacisz, rezerwacja wygaśnie sama po ok. 30 minutach.',
    }
  }
  if (status === 409 && typeof detail === 'object' && detail !== null && !Array.isArray(detail)) {
    const { message, unavailable_variant_ids: ids } = detail as Record<string, unknown>
    return {
      ...none,
      message: typeof message === 'string' ? `${message} Zmień ilość w koszyku i spróbuj ponownie.` : CART_ERROR,
      unavailableVariantIds: Array.isArray(ids) ? ids.filter((id): id is number => typeof id === 'number') : [],
    }
  }
  if (status === 422 && Array.isArray(detail)) {
    const { fields, general } = apiErrorsToFields(detail as ApiValidationError[])
    return { ...none, fields, message: general ? CART_ERROR : null }
  }
  // 422 below the Stripe minimum, 502 Stripe, 503 settings: the backend already wrote it in Polish.
  if (typeof detail === 'string') return { ...none, message: detail }
  return { ...none, message: GENERIC_ERROR }
}
