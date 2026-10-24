import { useSearchParams, Link } from 'react-router'
import { useState } from 'react'
import { Button } from '../components/Button'
import { ProductCard } from '../components/ProductCard'
import { CATEGORIES, SORTS, filterAndSort, isCategoryId, type CategoryId, type SortId } from '../catalog'
import { candleCount } from '../format'
import { useProducts } from '../useProducts'
import styles from './ShopPage.module.css'

export function ShopPage() {
  const productsState = useProducts()
  const [searchParams, setSearchParams] = useSearchParams()
  const [sort, setSort] = useState<SortId>('recommended')

  const param = searchParams.get('kategoria')
  const category: CategoryId = isCategoryId(param) ? param : 'all'

  const pickCategory = (id: CategoryId) => {
    setSearchParams(id === 'all' ? {} : { kategoria: id }, { replace: true })
  }

  return (
    <>
      <section className={`wrap ${styles.intro}`}>
        <nav aria-label="Okruszki" className={styles.breadcrumbs}>
          <Link to="/">Strona główna</Link> / Sklep
        </nav>
        <h1 className={`disp ${styles.title}`}>
          <span className={styles.line}>
            <span>Wszystkie świeczki</span>
          </span>
        </h1>
        <p className={styles.lead}>
          <span className={styles.leadLong}>
            Każda wylewana ręcznie, w małych partiach. Kolor gipsu wybierasz na karcie produktu, a po najechaniu
            świeczka się zapala.
          </span>
          <span className={styles.leadShort}>Kolor gipsu wybierasz na karcie produktu.</span>
        </p>
      </section>

      <section className={styles.controlsSection}>
        <div className={`wrap ${styles.controlsWrap}`}>
          <div className={styles.controls}>
            <div role="group" aria-label="Kategorie" className={styles.pills}>
              {CATEGORIES.map(({ id, label }) => (
                <button
                  key={id}
                  type="button"
                  className={styles.pill}
                  aria-pressed={category === id}
                  onClick={() => pickCategory(id)}
                >
                  {label}
                </button>
              ))}
            </div>
            <label className={styles.sort}>
              Sortuj
              <select value={sort} onChange={(event) => setSort(event.target.value as SortId)}>
                {SORTS.map(({ id, label }) => (
                  <option key={id} value={id}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </div>
      </section>

      <section className={`wrap ${styles.results}`}>
        <ShopResults state={productsState} category={category} sort={sort} onShowAll={() => pickCategory('all')} />
      </section>
    </>
  )
}

type ShopResultsProps = {
  state: ReturnType<typeof useProducts>
  category: CategoryId
  sort: SortId
  onShowAll: () => void
}

function ShopResults({ state, category, sort, onShowAll }: ShopResultsProps) {
  if (state.status === 'loading') {
    return (
      <p className={styles.status} role="status">
        Wyciągamy świeczki z form…
      </p>
    )
  }

  if (state.status === 'error' || state.status === 'not-found') {
    return (
      <div className={styles.message} role="alert">
        <h2 className={`disp ${styles.messageTitle}`}>Nie udało się wczytać świeczek</h2>
        <p>Sprawdź połączenie z internetem i spróbuj jeszcze raz.</p>
        <Button onClick={state.reload}>Spróbuj ponownie</Button>
      </div>
    )
  }

  const shown = filterAndSort(state.data, category, sort)

  return (
    <>
      <p className={styles.count} aria-live="polite">
        {candleCount(shown.length)}
      </p>
      {shown.length > 0 ? (
        <div className={styles.grid}>
          {shown.map((product, i) => (
            <ProductCard key={product.slug} product={product} index={i} />
          ))}
        </div>
      ) : (
        <div className={styles.message}>
          <svg className={styles.emptyCandle} viewBox="0 6 200 192" aria-hidden="true">
            <use href="#pm-pot" />
            <path d="M100 55 C95 46 105 41 100 31" />
          </svg>
          <h2 className={`disp ${styles.messageTitle}`}>Tu jeszcze nic się nie pali</h2>
          <p>W tej kategorii nie ma teraz świeczek. Nowa partia wychodzi z form w [termin].</p>
          <Button onClick={onShowAll}>Pokaż wszystkie świeczki</Button>
        </div>
      )}
    </>
  )
}
