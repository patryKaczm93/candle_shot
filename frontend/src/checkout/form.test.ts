import { describe, expect, it } from 'vitest'
import { isStripeCheckoutUrl } from '../api'
import {
  EMPTY_FORM,
  MESSAGES,
  apiErrorsToFields,
  describeCheckoutFailure,
  firstInvalid,
  isValidNip,
  toCheckoutRequest,
  validate,
  type CheckoutForm,
} from './form'

const valid: CheckoutForm = {
  ...EMPTY_FORM,
  email: 'anna@example.com',
  phone: '500 600 700',
  fullName: 'Anna Kowalska',
  lockerId: 'WAW01M',
  terms: true,
}

describe('validate', () => {
  it('accepts a complete locker order', () => {
    expect(validate(valid)).toEqual({})
  })

  it('reports every missing field of an empty form, first one is the e-mail', () => {
    const errors = validate(EMPTY_FORM)
    expect(Object.keys(errors).sort()).toEqual(['email', 'fullName', 'lockerId', 'phone', 'terms'])
    expect(errors.terms).toBe(MESSAGES.terms)
    expect(firstInvalid(errors)).toBe('email')
  })

  it.each([
    ['email', 'anna@'],
    ['email', 'anna example.com'],
    ['phone', '123'],
    ['phone', '500-600-70a'],
    ['lockerId', 'ab'],
  ] as const)('rejects %s = %j', (field, value) => {
    expect(validate({ ...valid, [field]: value })[field]).toBe(MESSAGES[field])
  })

  it('requires the address only for the courier', () => {
    const courier = { ...valid, method: 'courier' as const, lockerId: '' }
    expect(Object.keys(validate(courier)).sort()).toEqual(['addressLine', 'city', 'postalCode'])
    expect(
      validate({ ...courier, addressLine: 'ul. Lipowa 5/2', postalCode: '00-950', city: 'Warszawa' }),
    ).toEqual({})
    expect(validate({ ...courier, addressLine: 'ul. Lipowa 5', postalCode: '00950', city: 'Kraków' })).toEqual({
      postalCode: MESSAGES.postalCode,
    })
  })

  it('checks the NIP and company name only when an invoice is wanted', () => {
    expect(validate({ ...valid, nip: 'zły' })).toEqual({})
    const invoice = { ...valid, wantsInvoice: true }
    expect(validate({ ...invoice, nip: '1234567890', invoiceName: '' })).toEqual({
      nip: MESSAGES.nip,
      invoiceName: MESSAGES.invoiceName,
    })
    expect(validate({ ...invoice, nip: 'PL 526-000-12-46', invoiceName: 'Pracownia' })).toEqual({})
  })
})

describe('isValidNip', () => {
  it.each([
    ['5260001246', true],
    ['5260001247', false],
    ['123', false],
    ['526000124a', false],
  ])('%s → %s', (nip, expected) => {
    expect(isValidNip(nip)).toBe(expected)
  })
})

describe('toCheckoutRequest', () => {
  it('sends only variant ids and quantities, and the chosen delivery', () => {
    const body = toCheckoutRequest({ ...valid, email: ' anna@example.com ' }, [{ variantId: 7, qty: 10 }])

    expect(body).toEqual({
      email: 'anna@example.com',
      phone: '500 600 700',
      full_name: 'Anna Kowalska',
      shipping: { method: 'locker', locker_id: 'WAW01M' },
      invoice: null,
      terms_accepted: true,
      items: [{ variant_id: 7, qty: 10 }],
    })
    expect(JSON.stringify(body)).not.toMatch(/price|grosze/)
  })

  it('sends the courier address instead of the locker', () => {
    const body = toCheckoutRequest(
      { ...valid, method: 'courier', addressLine: 'ul. Lipowa 5', postalCode: '00-950', city: 'Warszawa' },
      [],
    )
    expect(body.shipping).toEqual({
      method: 'courier',
      address_line: 'ul. Lipowa 5',
      postal_code: '00-950',
      city: 'Warszawa',
    })
  })
})

describe('apiErrorsToFields', () => {
  it('maps Pydantic error locations to form fields', () => {
    const result = apiErrorsToFields([
      { loc: ['body', 'email'], msg: 'Value error, Nieprawidłowy adres e-mail' },
      { loc: ['body', 'shipping', 'courier', 'postal_code'], msg: 'x' },
      { loc: ['body', 'invoice', 'name'], msg: 'x' },
      { loc: ['body', 'terms_accepted'], msg: 'x' },
    ])
    expect(result).toEqual({
      fields: {
        email: MESSAGES.email,
        postalCode: MESSAGES.postalCode,
        invoiceName: MESSAGES.invoiceName,
        terms: MESSAGES.terms,
      },
      general: false,
    })
  })

  it('treats errors outside the form (e.g. cart items) as general', () => {
    expect(apiErrorsToFields([{ loc: ['body', 'items', 0, 'qty'], msg: 'x' }])).toEqual({
      fields: {},
      general: true,
    })
  })
})

describe('describeCheckoutFailure', () => {
  it('lists unavailable variants for 409', () => {
    const failure = describeCheckoutFailure(409, {
      message: 'Część produktów nie jest już dostępna w wybranej ilości.',
      unavailable_variant_ids: [3, 'x'],
    })
    expect(failure.unavailableVariantIds).toEqual([3])
    expect(failure.message).toMatch(/^Część produktów/)
  })

  it('puts 422 field errors next to the fields', () => {
    const failure = describeCheckoutFailure(422, [{ loc: ['body', 'phone'], msg: 'x' }])
    expect(failure).toEqual({ fields: { phone: MESSAGES.phone }, message: null, unavailableVariantIds: [] })
  })

  it('shows backend text for 422/502/503 and a generic text otherwise', () => {
    expect(describeCheckoutFailure(502, 'Nie udało się połączyć z systemem płatności.').message).toBe(
      'Nie udało się połączyć z systemem płatności.',
    )
    expect(describeCheckoutFailure(500, undefined).message).toMatch(/^Nie udało się złożyć/)
    expect(describeCheckoutFailure(null, undefined).message).toMatch(/^Nie udało się połączyć ze sklepem/)
  })
})

describe('isStripeCheckoutUrl', () => {
  it.each([
    ['https://checkout.stripe.com/c/pay/cs_test_1', true],
    ['https://checkout.stripe.com.evil.example/c/pay', false],
    ['http://checkout.stripe.com/c/pay', false],
    ['undefined', false],
    [undefined, false],
  ])('%s → %s', (url, expected) => {
    expect(isStripeCheckoutUrl(url)).toBe(expected)
  })
})
