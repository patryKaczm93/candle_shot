import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { addItem, cartCount, removeItem, setQty, type Cart } from './cart'
import { CartContext } from './cartContextValue'
import { CART_STORAGE_KEY, browserStorage, loadCart, parseCart, saveCart } from './storage'

export function CartProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<Cart>(() => loadCart(browserStorage()))

  useEffect(() => {
    saveCart(browserStorage(), items)
  }, [items])

  // Keep tabs in sync: another tab changed the cart.
  useEffect(() => {
    const onStorage = (event: StorageEvent) => {
      if (event.key === CART_STORAGE_KEY) setItems(parseCart(event.newValue))
    }
    window.addEventListener('storage', onStorage)
    return () => window.removeEventListener('storage', onStorage)
  }, [])

  const add = useCallback((variantId: number, qty: number, max?: number) => {
    setItems((cart) => addItem(cart, variantId, qty, max))
  }, [])
  const changeQty = useCallback((variantId: number, qty: number) => {
    setItems((cart) => setQty(cart, variantId, qty))
  }, [])
  const remove = useCallback((variantId: number) => {
    setItems((cart) => removeItem(cart, variantId))
  }, [])
  const clear = useCallback(() => setItems([]), [])

  const value = useMemo(
    () => ({ items, count: cartCount(items), add, setQty: changeQty, remove, clear }),
    [items, add, changeQty, remove, clear],
  )

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>
}
