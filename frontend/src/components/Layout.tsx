import { useEffect } from 'react'
import { Outlet, useLocation } from 'react-router'
import { BrandSprite } from './BrandSprite'
import { Footer } from './Footer'
import { Header } from './Header'

export function Layout() {
  // TODO(4.1): cart count from useCart.
  const cartCount = 0
  useScrollOnNavigate()

  return (
    <>
      <BrandSprite />
      <Header cartCount={cartCount} />
      <main>
        <Outlet />
      </main>
      <Footer />
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
