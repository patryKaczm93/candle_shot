import { describe, expect, it } from 'vitest'
import { candleCount, cartLabel, formatPrice, pluralPl } from './format'

const forms: [string, string, string] = ['produkt', 'produkty', 'produktów']

describe('pluralPl', () => {
  it.each([
    [0, 'produktów'],
    [1, 'produkt'],
    [2, 'produkty'],
    [4, 'produkty'],
    [5, 'produktów'],
    [12, 'produktów'],
    [14, 'produktów'],
    [22, 'produkty'],
    [25, 'produktów'],
    [112, 'produktów'],
    [104, 'produkty'],
  ])('%i → %s', (count, expected) => {
    expect(pluralPl(count, forms)).toBe(expected)
  })
})

describe('cartLabel', () => {
  it('describes an empty cart', () => {
    expect(cartLabel(0)).toBe('Koszyk, pusty')
  })

  it('uses the correct plural form', () => {
    expect(cartLabel(1)).toBe('Koszyk, 1 produkt')
    expect(cartLabel(3)).toBe('Koszyk, 3 produkty')
    expect(cartLabel(10)).toBe('Koszyk, 10 produktów')
  })
})

describe('formatPrice', () => {
  // Intl uses a non-breaking space before "zł"; normalise for readable expectations.
  const price = (grosze: number) => formatPrice(grosze).replace(/\s/g, ' ')

  it('formats grosze as Polish złoty', () => {
    expect(price(4900)).toBe('49,00 zł')
    expect(price(6450)).toBe('64,50 zł')
    expect(price(1)).toBe('0,01 zł')
  })

  it('groups thousands', () => {
    expect(price(124900)).toBe('1249,00 zł')
    expect(price(1234500)).toBe('12 345,00 zł')
  })
})

describe('candleCount', () => {
  it('uses the correct plural form', () => {
    expect(candleCount(1)).toBe('1 świeczka')
    expect(candleCount(4)).toBe('4 świeczki')
    expect(candleCount(5)).toBe('5 świeczek')
    expect(candleCount(0)).toBe('0 świeczek')
  })
})
