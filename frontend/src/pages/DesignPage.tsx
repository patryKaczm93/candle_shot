import type { ReactNode } from 'react'
import { Badge } from '../components/Badge'
import { Button } from '../components/Button'
import { IconButton } from '../components/IconButton'
import { CartIcon, MenuIcon } from '../components/icons'
import { Logo } from '../components/Logo'
import { cartLabel } from '../format'
import styles from './DesignPage.module.css'

// Internal component gallery for comparing with docs/design/screens.
export function DesignPage() {
  return (
    <div className={`wrap ${styles.page}`}>
      <h1 className={`disp ${styles.title}`}>System designu</h1>
      <p className={styles.lead}>
        Elementy bazowe z makiety. Nagłówek i stopka są na górze i na dole tej strony.
      </p>

      <Section title="Logo">
        <Logo />
        <div className={styles.dark}>
          <Logo variant="footer" />
        </div>
      </Section>

      <Section title="Przyciski">
        <Button arrow>Do sklepu</Button>
        <Button variant="ghost">Jak powstają</Button>
        <Button to="/design" arrow>
          Link jako przycisk
        </Button>
        <Button disabled>Wyprzedana</Button>
        <Button variant="ghost" disabled>
          Nieaktywny
        </Button>
      </Section>

      <Section title="Przycisk ikony z licznikiem">
        {[0, 2, 10].map((count) => (
          <IconButton key={count} label={cartLabel(count)} count={count}>
            <CartIcon />
          </IconButton>
        ))}
        <IconButton label="Otwórz menu">
          <MenuIcon />
        </IconButton>
      </Section>

      <Section title="Odznaki">
        <Badge>Bestseller</Badge>
        <Badge>Nowość</Badge>
        <Badge>Ostatnia sztuka</Badge>
        <Badge>Prezent</Badge>
        <div className={styles.narrow}>
          <Badge>Bardzo długa odznaka, która musi się przyciąć</Badge>
        </div>
        <Badge count>2</Badge>
        <Badge count>10</Badge>
      </Section>
    </div>
  )
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className={styles.section}>
      <h2 className={`disp ${styles.sectionTitle}`}>{title}</h2>
      <div className={styles.row}>{children}</div>
    </section>
  )
}
