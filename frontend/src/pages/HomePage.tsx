import { useState, type CSSProperties } from 'react'
import offerCustomSvg from '../assets/illustrations/offer-custom.svg?raw'
import offerMouldSvg from '../assets/illustrations/offer-mould.svg?raw'
import ringBadgeSvg from '../assets/illustrations/ring-badge.svg?raw'
import stepCadSvg from '../assets/illustrations/step-cad.svg?raw'
import stepPlasterSvg from '../assets/illustrations/step-plaster.svg?raw'
import stepPrintSvg from '../assets/illustrations/step-print.svg?raw'
import stepSiliconeSvg from '../assets/illustrations/step-silicone.svg?raw'
import stepWaxSvg from '../assets/illustrations/step-wax.svg?raw'
import { Button } from '../components/Button'
import { CandleIllustration } from '../components/CandleIllustration'
import { Illustration } from '../components/Illustration'
import { mailto } from '../shop'
import styles from './HomePage.module.css'

// Plaster colours from the mockup; on the home page they only recolour the hero illustration.
const PLASTER_COLOURS = [
  { name: 'naturalny biały', hex: '#FFFFFF' },
  { name: 'terakota', hex: '#D9A27A' },
  { name: 'szałwia', hex: '#B9C2A4' },
  { name: 'grafit', hex: '#8C8178' },
]

const TRUST = [
  'Wosk sojowy',
  'Formy projektowane w 3D',
  'Naczynia z gipsu, odlewane ręcznie',
  'Bawełniany knot',
  'Wysyłka InPost',
  'Małe partie',
]

const STEPS = [
  {
    svg: stepCadSvg,
    title: 'Projektujemy kształt w 3D',
    text: 'Każde naczynie zaczyna się w programie CAD. Rysujemy w nim kształt i model, z którego potem powstanie forma.',
  },
  {
    svg: stepPrintSvg,
    title: 'Drukujemy model na drukarce 3D',
    text: 'Model rośnie warstwa po warstwie. Potem go szlifujemy, bo każda rysa odbiłaby się później na gipsie.',
  },
  {
    svg: stepSiliconeSvg,
    title: 'Wylewamy formę silikonową',
    text: 'Wydruk zalewamy silikonem. Po związaniu wyjmujemy model, a w silikonie zostaje jego dokładny negatyw.',
  },
  {
    svg: stepPlasterSvg,
    title: 'Odlewamy naczynie z gipsu',
    text: 'Do formy silikonowej wlewamy gips. Każde naczynie schnie osobno i ma swoje drobne niedoskonałości.',
  },
  {
    svg: stepWaxSvg,
    title: 'Wylewamy wosk i czekamy',
    text: 'Wosk sojowy z olejkiem trafia do naczynia, na wycentrowany knot. Świeczka dojrzewa [X] dni, zanim trafi do paczki.',
  },
]

const CUSTOM_STEPS = [
  'Wysyłasz pomysł. Wystarczy szkic, zdjęcie albo kilka zdań.',
  'Wyceniamy projekt i formę, zanim cokolwiek zaczniemy.',
  'Akceptujesz model 3D, a my robimy formy i wylewamy świeczki.',
]

const delay = (i: number) => ({ '--i': i }) as CSSProperties

export function HomePage() {
  return (
    <>
      <Hero />
      <TrustStrip />
      {/* TODO(3.1): "Najchętniej zapalane" product grid, once GET /api/products exists (2.1). */}
      <Workshop />
      <CustomOrders />
      {/* Customer reviews stay hidden until there are real ones (docs/design/DESIGN.md). */}
    </>
  )
}

function Hero() {
  const [colour, setColour] = useState(0)
  const [lit, setLit] = useState(true)
  const current = PLASTER_COLOURS[colour]

  return (
    <section className={`wrap ${styles.hero}`}>
      <div className={styles.heroText}>
        <h1 className={`disp ${styles.heroTitle}`}>
          <span className={styles.line}>
            <span style={delay(0)}>Świeczki, które</span>
          </span>
          <span className={styles.line}>
            <span style={delay(1)}>pachną domem.</span>
          </span>
        </h1>
        <p className={`${styles.load} ${styles.heroLead}`} style={{ '--d': '420ms' } as CSSProperties}>
          Wylewamy je ręcznie w formach z gipsu, w [miasto]. Wosk sojowy, bawełniany knot i zapach, który zostaje w
          pokoju długo po zgaszeniu.
        </p>
        <div className={`${styles.load} ${styles.heroActions}`} style={{ '--d': '520ms' } as CSSProperties}>
          <Button to="/sklep" arrow>
            Zobacz świeczki
          </Button>
          <Button variant="ghost" href="#pracownia">
            Jak powstają
          </Button>
        </div>
      </div>

      <div className={styles.heroVisual}>
        <div className={styles.panel}>
          <div className={styles.panelInner}>
            <svg className={styles.petals} viewBox="0 0 600 580" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
              <g className={styles.petalGroup}>
                <circle cx="90" cy="70" r="36" />
                <circle cx="140" cy="106" r="36" />
                <circle cx="121" cy="165" r="36" />
                <circle cx="59" cy="165" r="36" />
                <circle cx="40" cy="106" r="36" />
              </g>
              <g className={styles.petalGroup}>
                <circle cx="520" cy="430" r="30" />
                <circle cx="562" cy="460" r="30" />
                <circle cx="546" cy="510" r="30" />
                <circle cx="494" cy="510" r="30" />
                <circle cx="478" cy="460" r="30" />
              </g>
            </svg>
            <CandleIllustration
              className={styles.heroCandle}
              gips={current.hex}
              lit={lit}
              label={`Świeczka w gipsie w kolorze ${current.name}, w tym miejscu zdjęcie produktu`}
            />
          </div>
          <div className={styles.panelControls}>
            <div role="group" aria-label="Kolor gipsu" className={styles.swatches}>
              <span className={styles.swatchesLabel}>Gips:</span>
              {PLASTER_COLOURS.map((option, i) => (
                <button
                  key={option.hex}
                  type="button"
                  className={styles.swatch}
                  style={{ background: option.hex }}
                  aria-label={`Gips ${option.name}`}
                  aria-pressed={colour === i}
                  onClick={() => setColour(i)}
                />
              ))}
            </div>
            <button type="button" className={styles.chip} aria-pressed={lit} onClick={() => setLit(!lit)}>
              {lit ? 'Zgaś' : 'Zapal'}
            </button>
          </div>
        </div>
        <Illustration svg={ringBadgeSvg} className={styles.ringBadge} />
      </div>
    </section>
  )
}

function TrustStrip() {
  return (
    <section aria-label="Co jest w każdej świeczce" className={styles.trust}>
      <ul className={styles.marquee}>
        {[...TRUST, ...TRUST].map((item, i) => (
          <li key={i} className={styles.trustItem} aria-hidden={i >= TRUST.length ? true : undefined}>
            <svg width="32" height="28" viewBox="0 6 200 174" aria-hidden="true">
              <use href="#pm-mark-b" />
            </svg>
            {item}
          </li>
        ))}
      </ul>
    </section>
  )
}

function Workshop() {
  return (
    <section id="pracownia" className={styles.workshop}>
      <div className="wrap">
        <div className={styles.sectionHead}>
          <h2 className={`disp ${styles.sectionTitle} ${styles.reveal}`}>Jak powstaje świeczka</h2>
          <p className={`${styles.sectionLead} ${styles.reveal}`}>
            Zanim zapalisz świeczkę, jej kształt przejdzie przez komputer, drukarkę 3D, silikon i gips. Od projektu do
            paczki mija [X] dni.
          </p>
        </div>
      </div>
      <ol className={`wrap ${styles.steps}`}>
        {STEPS.map((step) => (
          <li key={step.title} className={styles.step}>
            <Illustration svg={step.svg} className={styles.stepPicture} />
            <h3 className={`disp ${styles.stepTitle}`}>{step.title}</h3>
            <p className={styles.stepText}>{step.text}</p>
          </li>
        ))}
      </ol>
    </section>
  )
}

function CustomOrders() {
  return (
    <section id="na-zamowienie" className={`wrap ${styles.custom}`}>
      <div className={styles.customIntro}>
        <h2 className={`disp ${styles.sectionTitle} ${styles.reveal}`}>Świeczka w&nbsp;Twoim kształcie</h2>
        <p className={`${styles.sectionLead} ${styles.reveal}`}>
          Masz pomysł na własne naczynie? Logo firmy, kształt na prezent ślubny, coś, czego nie ma nikt inny.
          Zaprojektujemy je od zera i wylejemy w nim świeczki.
        </p>
        <ul className={styles.customSteps}>
          {CUSTOM_STEPS.map((text) => (
            <li key={text}>
              <svg width="24" height="21" viewBox="0 6 200 174" aria-hidden="true">
                <use href="#pm-mark-b" />
              </svg>
              <span>{text}</span>
            </li>
          ))}
        </ul>
        <div className={styles.customActions}>
          <Button href={mailto('Świeczka na zamówienie')} arrow>
            Opisz swój pomysł
          </Button>
          <Button variant="ghost" href={mailto('Forma silikonowa')}>
            Zapytaj o formę
          </Button>
        </div>
      </div>

      <div className={styles.offers}>
        <article className={styles.offer}>
          <Illustration svg={offerCustomSvg} className={styles.offerPicture} />
          <div className={styles.offerBody}>
            <h3 className={`disp ${styles.offerTitle}`}>Świeczka na zamówienie</h3>
            <p>Do ceny świeczek doliczamy jednorazowo koszt wykonania projektu i formy silikonowej do odlewów.</p>
            <dl className={styles.priceList}>
              <div>
                <dt>Projekt 3D w CAD</dt>
                <dd>od [kwota] zł</dd>
              </div>
              <div>
                <dt>Forma silikonowa do odlewów</dt>
                <dd>od [kwota] zł</dd>
              </div>
              <div>
                <dt>Świeczki</dt>
                <dd>wg wyceny</dd>
              </div>
            </dl>
            <p className={styles.offerNote}>
              Minimalne zamówienie: [X] sztuk. Przy kolejnej partii z tej samej formy płacisz już tylko za świeczki.
            </p>
          </div>
        </article>

        <article className={`${styles.offer} ${styles.offerDark}`}>
          <Illustration svg={offerMouldSvg} className={styles.offerPicturePlain} />
          <div className={styles.offerBody}>
            <h3 className={`disp ${styles.offerTitle}`}>Sama forma silikonowa</h3>
            <p>
              Robisz świeczki, mydła albo odlewy z gipsu? Zaprojektujemy i wykonamy dla Ciebie formę silikonową, według
              Twojego wzoru albo pliku 3D.
            </p>
            <p className={styles.offerPrice}>Od [kwota] zł, realizacja [X] dni</p>
          </div>
        </article>
      </div>
    </section>
  )
}
