import { Outlet } from 'react-router'
import { Footer } from './Footer'
import { Header } from './Header'

export function Layout() {
  // TODO(4.1): cart count from useCart.
  const cartCount = 0

  return (
    <>
      <Header cartCount={cartCount} />
      <main>
        <Outlet />
      </main>
      <Footer />
    </>
  )
}
