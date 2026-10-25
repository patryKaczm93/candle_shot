import { useState, type CSSProperties } from 'react'
import { Link } from 'react-router'
import { cartLabel } from '../format'
import { Badge } from './Badge'
import { Button } from './Button'
import { IconButton } from './IconButton'
import { CartIcon, CloseIcon, MenuIcon } from './icons'
import { Logo } from './Logo'
import styles from './Header.module.css'

const NAV_LINKS = [
  { href: '/sklep', label: 'Sklep' },
  { href: '/#pracownia', label: 'Jak powstają' },
  { href: '/#na-zamowienie', label: 'Na zamówienie' },
  { href: '#kontakt', label: 'Kontakt' },
]

type HeaderProps = {
  cartCount: number
  onOpenCart: () => void
}

export function Header({ cartCount, onOpenCart }: HeaderProps) {
  const [menuOpen, setMenuOpen] = useState(false)
  const closeMenu = () => setMenuOpen(false)

  return (
    <header className={styles.header}>
      <div className={`wrap ${styles.bar}`}>
        <Logo />

        <nav className={styles.nav} aria-label="Główna">
          {NAV_LINKS.map((link) => (
            <NavLink key={link.href} {...link} className={styles.navLink} />
          ))}
        </nav>

        <Button
          variant="ghost"
          className={styles.cartDesktop}
          aria-haspopup="dialog"
          aria-label={cartLabel(cartCount)}
          onClick={onOpenCart}
        >
          <CartIcon />
          Koszyk
          {cartCount > 0 && <Badge count>{cartCount}</Badge>}
        </Button>

        <div className={styles.mobileActions}>
          <IconButton label={cartLabel(cartCount)} count={cartCount} aria-haspopup="dialog" onClick={onOpenCart}>
            <CartIcon />
          </IconButton>
          <IconButton
            label={menuOpen ? 'Zamknij menu' : 'Otwórz menu'}
            aria-expanded={menuOpen}
            aria-controls="menu-mobile"
            onClick={() => setMenuOpen((open) => !open)}
          >
            {menuOpen ? <CloseIcon /> : <MenuIcon />}
          </IconButton>
        </div>
      </div>

      {menuOpen && (
        <nav id="menu-mobile" className={styles.menu} aria-label="Główna">
          {NAV_LINKS.map((link, i) => (
            <NavLink
              key={link.href}
              {...link}
              className={`disp ${styles.menuLink}`}
              style={{ '--i': i } as CSSProperties}
              onClick={closeMenu}
            />
          ))}
        </nav>
      )}
    </header>
  )
}

type NavLinkProps = {
  href: string
  label: string
  className: string
  style?: CSSProperties
  onClick?: () => void
}

function NavLink({ href, label, ...rest }: NavLinkProps) {
  // In-page anchors (#kontakt) stay plain links; paths, also with a #section, go through the router.
  if (href.startsWith('#')) {
    return (
      <a href={href} {...rest}>
        {label}
      </a>
    )
  }
  return (
    <Link to={href} {...rest}>
      {label}
    </Link>
  )
}
