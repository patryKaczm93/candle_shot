import { describe, expect, it } from 'vitest'
import { CART_STORAGE_KEY, loadCart, parseCart, saveCart } from './storage'

/** Minimal in-memory Storage, standing in for the browser's localStorage. */
function memoryStorage(): Storage {
  const data = new Map<string, string>()
  return {
    get length() {
      return data.size
    },
    clear: () => data.clear(),
    getItem: (key) => data.get(key) ?? null,
    key: (i) => [...data.keys()][i] ?? null,
    removeItem: (key) => void data.delete(key),
    setItem: (key, value) => void data.set(key, value),
  }
}

function throwingStorage(): Storage {
  const fail = () => {
    throw new Error('localStorage is blocked')
  }
  return { length: 0, clear: fail, getItem: fail, key: fail, removeItem: fail, setItem: fail }
}

describe('cart storage', () => {
  it('survives a page reload (save, then load in a fresh page)', () => {
    const storage = memoryStorage()
    const cart = [
      { variantId: 3, qty: 2 },
      { variantId: 9, qty: 1 },
    ]
    saveCart(storage, cart)

    expect(loadCart(storage)).toEqual(cart)
  })

  it('stores only ids and quantities', () => {
    const storage = memoryStorage()
    saveCart(storage, [{ variantId: 3, qty: 2 }])

    expect(JSON.parse(storage.getItem(CART_STORAGE_KEY) ?? '')).toEqual([{ variantId: 3, qty: 2 }])
  })

  it('starts empty when nothing is stored', () => {
    expect(loadCart(memoryStorage())).toEqual([])
    expect(loadCart(undefined)).toEqual([])
  })

  it('does not crash when localStorage is blocked', () => {
    expect(loadCart(throwingStorage())).toEqual([])
    expect(() => saveCart(throwingStorage(), [{ variantId: 1, qty: 1 }])).not.toThrow()
  })
})

describe('parseCart', () => {
  it.each(['not json', '{"variantId":1}', 'null', ''])('returns an empty cart for %j', (raw) => {
    expect(parseCart(raw)).toEqual([])
  })

  it('drops invalid lines, duplicates and extra fields, caps qty at 10', () => {
    const raw = JSON.stringify([
      { variantId: 1, qty: 2, price_grosze: 1 },
      { variantId: 1, qty: 5 },
      { variantId: 2, qty: 0 },
      { variantId: 3, qty: 1.5 },
      { variantId: '4', qty: 1 },
      { variantId: 5, qty: 99 },
      null,
    ])

    expect(parseCart(raw)).toEqual([
      { variantId: 1, qty: 2 },
      { variantId: 5, qty: 10 },
    ])
  })
})
