import styles from './HomePage.module.css'

// Placeholder until story 3.3 builds the real home page from the mockup.
export function HomePage() {
  return (
    <section className={`wrap ${styles.placeholder}`}>
      <h1 className={`disp ${styles.title}`}>Pachnie miło</h1>
      <p>Ręcznie robione świeczki w formach z gipsu. Sklep wkrótce.</p>
    </section>
  )
}
