import { useEffect } from 'react'
import { Outlet, useLocation } from 'react-router'
import { useCart } from '../cart/useCart'
import { BrandSprite } from './BrandSprite'
import { CartDrawer } from './CartDrawer'
import { Footer } from './Footer'
import { Header } from './Header'

export function Layout() {
  const { count: cartCount, open: openCart, close: closeCart } = useCart()
  const { pathname } = useLocation()
  useScrollOnNavigate()

  // Links inside the drawer navigate away: close it on every page change.
  useEffect(() => closeCart(), [pathname, closeCart])

  return (
    <>
      <BrandSprite />
      <Header cartCount={cartCount} onOpenCart={openCart} />
      <main>
        <Outlet />
      </main>
      <Footer />
      <CartDrawer />
    </>
  )
}

// The router does not scroll by itself: go to the #section from the URL, or to the top of a new page.
function useScrollOnNavigate() {
  const { pathname, hash } = useLocation()

  useEffect(() => {
    if (hash) {
      document.getElementById(decodeURIComponent(hash.slice(1)))?.scrollIntoView()
    } else {
      window.scrollTo(0, 0)
    }
  }, [pathname, hash])
}
