import { Link } from 'react-router'
import { CONTACT_EMAIL } from '../shop'
import { Logo } from './Logo'
import styles from './Footer.module.css'

export function Footer() {
  return (
    <footer id="kontakt" className={styles.footer}>
      <div className={`wrap ${styles.columns}`}>
        <div className={styles.brand}>
          <Logo variant="footer" />
          <p className={styles.tagline}>Ręcznie robione świeczki w formach z gipsu.</p>
        </div>

        <div className={`${styles.column} ${styles.shopColumn}`}>
          <span className={styles.heading}>Sklep</span>
          <Link to="/sklep">Wszystkie świeczki</Link>
          <Link to="/sklep">Zestawy prezentowe</Link>
          <Link to="/#na-zamowienie">Na zamówienie</Link>
        </div>

        <div className={styles.column}>
          <span className={styles.heading}>Pomoc</span>
          <Link to="/dostawa-i-zwroty">Dostawa i zwroty</Link>
          <Link to="/regulamin">Regulamin</Link>
          <Link to="/polityka-prywatnosci">Polityka prywatności</Link>
        </div>

        <div className={styles.column}>
          <span className={styles.heading}>Kontakt</span>
          <a href={`mailto:${CONTACT_EMAIL}`} className={styles.email}>
            {CONTACT_EMAIL}
          </a>
          {/* TODO(9.3): real Instagram link. */}
          <a href="#">Instagram</a>
          <Link to="/#na-zamowienie">Świeczki i formy na zamówienie</Link>
        </div>
      </div>

      <div className={`wrap ${styles.bigWordmarkWrap}`}>
        <p className={`disp ${styles.bigWordmark}`} aria-hidden="true">
          Pachnie miło
        </p>
      </div>

      {/* TODO(9.3): seller name and NIP. */}
      <div className={`wrap ${styles.copyright}`}>© Pachnie miło · [nazwa firmy, NIP]</div>
    </footer>
  )
}
