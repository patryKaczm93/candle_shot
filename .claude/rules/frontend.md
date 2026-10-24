---
paths:
  - "frontend/**/*.{ts,tsx,css}"
---

# Frontend (React + Vite)

- Wygląd budujemy według makiety. Przed pracą nad ekranem lub komponentem przeczytaj `docs/design/DESIGN.md`, obejrzyj zrzut z `docs/design/screens/` i sprawdź wartości w odpowiednim pliku `docs/design/mockups/*.dc.html` (mapa ekranów jest w DESIGN.md).
- Kolory, fonty, odstępy, promienie i cień tylko przez zmienne z `src/styles/tokens.css`. Nie wpisuj wartości hex ani px z makiety bezpośrednio, jeśli istnieje dla nich token.
- Style w zwykłych plikach CSS (CSS Modules `*.module.css` dla komponentów). Bez Tailwinda i bibliotek UI: wygląd jest własny.
- Logo wyłącznie to z makiety: znak `src/assets/logo-mark.svg` + logotyp „Pachnie / miło”, jako komponent `<Logo>` według sekcji „Logo” w `docs/design/DESIGN.md`. Nie twórz innego logo, nie upraszczaj go i nie zastępuj tekstem ani ikoną.
- Ilustracje produktów (doniczka w kolorze gipsu) z `src/assets/brand-sprite.svg`, jako komponent `<CandleIllustration gips="#B9C2A4">`.
- Animacje tylko w CSS i tylko w `@media (prefers-reduced-motion: no-preference)`.
- Po zbudowaniu ekranu wypisz, co mam porównać ze zrzutem w przeglądarce (szerokości 1440 px i 390 px), oraz znane różnice względem makiety.
- Struktura: `src/pages/` (ekrany), `src/components/`, `src/api.ts` (jedyne miejsce z `fetch`), `src/cart/` (hook `useCart` + localStorage).
- Bez globalnego state managera (Redux, Zustand). Wystarczą React state, Context dla koszyka i `fetch`.
- Adres API tylko z `import.meta.env.VITE_API_URL`.
- Koszyk przechowuje wyłącznie `{ variantId, qty }`. Ceny wyświetlane w koszyku pochodzą z API i są tylko informacyjne.
- Kwoty z API przychodzą w groszach; formatuj przez `Intl.NumberFormat('pl-PL', { style: 'currency', currency: 'PLN' })`.
- Dostępność: prawdziwe `<button>`, `<a href>`, `<label>` przy polach, `aria-label` przy przyciskach z samą ikoną. Działa na szerokości 390 px.
- Teksty dla klienta po polsku, z poprawną odmianą (1 produkt, 2 produkty, 5 produktów).
