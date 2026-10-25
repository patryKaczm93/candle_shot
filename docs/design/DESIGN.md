# Design — Pachnie miło

Źródło prawdy dla wyglądu sklepu: makieta „Pachnie miło — mockup v2 z animacjami” i system designu „Pachnie miło”. Budujemy UI tak, żeby wyglądał jak makieta. Jeśli coś wymaga odstępstwa, zapytaj, zamiast zgadywać.

## Pliki

| Ścieżka | Co to jest | Jak używać |
| --- | --- | --- |
| `screens/*.png` | Zrzuty każdego ekranu (komputer 1440 px, telefon 390 px) | Zawsze obejrzyj zrzut przed budową ekranu. Fonty na zrzutach są zastępcze: docelowo Fraunces i Nunito |
| `mockups/*.dc.html` | Kod makiet: dokładne style, teksty, stany, animacje, SVG | Źródło wartości (odstępy, rozmiary, teksty, keyframes). Nie kopiuj 1:1: to format edytora, nie React |
| `tokens.json` | System designu: kolory, typografia, odstępy, promienie, cień | Źródło tokenów |
| `frontend/src/styles/tokens.css` | Tokeny jako zmienne CSS | Używaj zmiennych, nie wpisuj kolorów ręcznie |
| `frontend/src/assets/logo-mark.svg` | Znak logo z makiety | Zawsze w logo (sekcja „Logo”) |
| `frontend/src/assets/brand-sprite.svg` | Doniczka i płomień jako symbole SVG | Ilustracje produktów do czasu prawdziwych zdjęć |

## Mapa ekranów

| Makieta (komputer / telefon) | Trasa w aplikacji | Historyjka |
| --- | --- | --- |
| `Main` / `Tel-Glowna` | `/` | 3.3 |
| `Sklep` / `Tel-Sklep` | `/sklep` | 3.1 |
| `Produkt` / `Tel-Produkt` | `/sklep/:slug` | 3.2 |
| `Koszyk` / `Tel-Koszyk` | szuflada nad bieżącą stroną (komputer: z prawej, 500 px; telefon: arkusz od dołu) | 4.2 |
| `Zamowienie` / `Tel-Zamowienie` | `/zamowienie` | 5.2 |

## Jak czytać pliki `.dc.html`

- Ważne: blok `<helmet><style>` (klasy i animacje), markup wewnątrz `<x-dc>` (struktura, style inline, teksty) i tablice danych w skrypcie (przykładowe produkty, opcje dostawy, kolory gipsu).
- Do pominięcia: `<script src="./support.js">`, atrybuty `hint-placeholder-*`, `data-props` i tryby testowe („Demo”, „Najgorszy przypadek”, „Pusty koszyk”). Te tryby to scenariusze do testowania wyglądu: długie nazwy, 10 sztuk, pusty stan. Warto je odtworzyć w testach i w ręcznym sprawdzaniu.
- Składnia szablonu: `{{wartosc}}` to dane, `<sc-for list=… as=…>` to `.map()`, `<sc-if value=…>` to warunek, `onClick="{{fn}}"` to handler, `renderVals()` to odpowiednik logiki komponentu.
- Linki między makietami (`href="Sklep.dc.html"`) zamieniaj na trasy z mapy wyżej.

## Logo (obowiązkowe, dokładnie jak w makiecie)

Logo = **znak** (doniczka z gipsu z płomieniem) + **logotyp** „Pachnie / miło” po prawej, w dwóch liniach. Nie projektuj nowego logo, nie upraszczaj go i nie zastępuj ikoną ani samym tekstem.

- Znak: `frontend/src/assets/logo-mark.svg` (to samo SVG co w nagłówku makiety). Importuj plik, nie przerysowuj kształtów. W nagłówku płomień ma migotać po najechaniu (animacja `lflick` z makiety), więc w komponencie `<Logo>` wstaw SVG inline, a płomień w osobnej grupie `<g>`.
- Logotyp: tekst HTML, nie obrazek. Fraunces 900, `font-variation-settings: "SOFT" 100, "WONK" 1`, `line-height: 0.92`, `letter-spacing: -0.01em`, kolor `--color-pomarancz`, `-webkit-text-stroke: 0.146em var(--color-braz)`, `paint-order: stroke fill`, `white-space: nowrap`, łamanie po „Pachnie”.
- Rozmiary z makiety: komputer znak 62×52 px + logotyp 25 px, odstęp 12 px; telefon znak 50×42 px + logotyp 20 px, odstęp 8 px.
- Logo jest linkiem do `/` z `aria-label="Pachnie miło, strona główna"`; SVG z `aria-hidden="true"`.
- Favicon: `frontend/public/favicon.svg` (sam znak).
- Ilustracje produktów w kartach i koszyku używają tej samej doniczki z `brand-sprite.svg` (`#pm-pot`, `#pm-pot-b`), z kolorem gipsu przez `--body` i `--rim`.

System designu wymienia też 4 oryginalne pliki logo od właściciela marki (JPG 2000×2000 z tłem). Makieta ich nie używa. Jeśli kiedyś zastąpimy nimi znak, to tylko w wersji SVG lub PNG z przezroczystym tłem i po decyzji właściciela.

## Fundamenty

- **Kolory:** tło `--color-krem`, karty i pola `--color-krem-jasny`, sekcje i tło zdjęć `--color-krem-ciemny`, tekst i obrysy `--color-braz`, tekst pomocniczy `--color-braz-miekki`, akcent `--color-pomarancz`. Pomarańcz nigdy nie służy jako kolor tekstu na kremie. Tekst na pomarańczu to `--color-braz-gleboki`. Sukces `--color-oliwka`, błąd `--color-terakota`.
- **Typografia:** nagłówki Fraunces 900 z osiami `font-variation-settings: "SOFT" 100, "WONK" 1` i `letter-spacing: -0.02em` (klasa `.disp`). Tekst Nunito 400–800. Google Fonts: `Fraunces:opsz,wght,SOFT,WONK@9..144,700..900,100,1` i `Nunito:wght@400;600;700;800`. Rozważ samohostowanie przez `@fontsource`.
- **Kształty:** obrys 2px w brązie na przyciskach, kartach, polach i odznakach. Przyciski jako pigułki (`999px`), karty 18–20px, duże bloki 28–36px.
- **Cień retro:** twardy `4px 4px 0` w brązie (`--cien-retro`) na przyciskach głównych. Po najechaniu przycisk unosi się o 2px, a cień rośnie do 6px. Po wciśnięciu przycisk przesuwa się o 3px i cień znika.
- **Ikony:** liniowe SVG o grubości 2–2.5, `stroke="currentColor"`, bez emoji.
- **Tekst w nawiasach kwadratowych** (`[kwota]`, `[X] dni`, `[termin]`) oznacza dane do uzupełnienia. Pobieraj je z API (`/api/shipping`, `settings`) albo zostaw jako TODO. Nie wymyślaj wartości.

## Komponenty z makiety

| Komponent | Klasa w makiecie | Uwagi |
| --- | --- | --- |
| Przycisk główny | `.btn.btn-main` | min. 52 px wysokości (54–56 px na telefonie), pomarańcz, cień retro, strzałka `→` przesuwa się po najechaniu |
| Przycisk drugorzędny | `.btn-ghost` | kremowe tło z obrysem |
| Przycisk ikony | `.icon-btn` | 46 px, okrągły, krem-jasny; koszyk z licznikiem `.badge` |
| Pigułka filtra | `.pill` | aktywna: brązowe tło, kremowy tekst; `aria-pressed` |
| Odznaka | `.badge` | „Bestseller”, „Nowość”, „Ostatnia sztuka”, „Prezent” |
| Karta produktu | `.card` | krem-jasny, obrys, tło zdjęcia krem-ciemny, nazwa `.disp` przycięta do 2 linii, cena tabularna |
| Wybór koloru gipsu | `.sw` | kółka w kolorze gipsu; aktywne z podwójnym pierścieniem |
| Licznik ilości | `.step` | pigułka z „−” i „+”, zakres 1–10, przyciski nieaktywne na granicach |
| Akordeon | `.acc` | „O zapachu”, „Jak palić bezpiecznie”, „Dostawa i zwroty”, „Własny kształt” |
| Szuflada koszyka | `aside.drawer` / `section.sheet` | półprzezroczyste tło `rgba(74,42,18,.5)`, pasek darmowej dostawy (pomarańcz, po progu oliwka) |
| Toast „Dodano do koszyka” | `.toast` | z linkiem „Koszyk →”, znika po ok. 4 s |
| Pole formularza | `.field` | etykieta nad polem, błąd w terakocie pod polem, `aria-invalid` |
| Pusty stan | — | doniczka bez płomienia + nagłówek w tonie marki („Tu jeszcze nic nie pachnie”) |

## Ruch

- Krzywe: `--ease-out` (przyciski, drobne przejścia), `--ease-expo` (wejścia elementów), `--ease-drawer` (szuflada).
- Wzorce: nagłówki wjeżdżają linia po linii (`.ln`), elementy pojawiają się z przesunięciem 12–20 px i kolejnym opóźnieniem 60–70 ms, liczby „przewijają się” przy zmianie (`.roll`), płomienie delikatnie migoczą (`flicker`).
- Wszystkie animacje tylko w `@media (prefers-reduced-motion: no-preference)`. Przy ograniczonym ruchu zostają wyłącznie zmiany koloru.
- Animacje CSS, bez bibliotek animacji.

## Zmiany względem makiety

- **Płatność:** blok wyboru BLIK / Przelewy24 / karta na ekranie zamówienia zastępujemy informacją „Zapłacisz BLIKIEM, Przelewy24 lub kartą na bezpiecznej stronie Stripe”. Przycisk „Zamawiam i płacę” przekierowuje na Stripe Checkout.
- **Zdjęcia:** ilustracje doniczek w makiecie zastępują zdjęcia. Kiedy zdjęcia będą gotowe, wchodzą w to samo miejsce (`aspect-ratio: 1/1`, tło krem-ciemny, promień 20 px).
- **Opinie klientów** na stronie głównej pokazujemy tylko prawdziwe. Do czasu ich zebrania sekcja jest ukryta.
- **Motyw „Wieczorny”** (ciemny) istnieje w tokenach, ale na start go nie włączamy.
- **Strona główna (decyzja właściciela):** sekcja „Świeczka w Twoim kształcie” nie przykleja się przy przewijaniu (bez `position: sticky`). W hero panel ze świeczką odsłania się od dołu, w tym samym kierunku co wjeżdżające linie nagłówka.
