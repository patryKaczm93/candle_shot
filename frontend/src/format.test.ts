import { describe, expect, it } from 'vitest'
import { cartLabel, pluralPl } from './format'

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
