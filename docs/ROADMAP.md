# Roadmapa — Pachnie miło

Jedna historyjka = jeden wieczór pracy. Realizacja: `/next-story` w Claude Code. Odhaczamy `- [x]` po spełnieniu „Gotowe, gdy” i przejściu testów.

## Faza 0 — Fundamenty

- [x] **0.1 Repozytorium.** Struktura `backend/` + `frontend/`, `docker-compose.yml` z PostgreSQL, `README.md` z poleceniami. Gotowe, gdy: `docker compose up -d db` startuje bazę, `.gitignore` obejmuje `.env`.
- [x] **0.2 Szkielet backendu.** uv + FastAPI + `pydantic-settings` + `GET /api/health` (z testem połączenia z bazą). Gotowe, gdy: `uv run uvicorn app.main:app` zwraca `{"status":"ok"}`, a ustawienia czytane są z `.env`.
- [x] **0.3 Szkielet frontendu i fundamenty designu.** Vite + React + TS + React Router; podpięte `src/styles/tokens.css` i fonty Fraunces + Nunito; komponenty bazowe z `docs/design/DESIGN.md`: komponent `<Logo>` (znak z `logo-mark.svg` + logotyp, jak w makiecie), favicon, nagłówek, stopka, przycisk główny i drugorzędny, przycisk ikony z licznikiem, odznaka. Gotowe, gdy: strona `/design` pokazuje te elementy i wygląda jak nagłówek, stopka i przyciski ze zrzutów.
- [x] **0.4 Konto Stripe w trybie testowym** + Stripe CLI. Gotowe, gdy: `stripe listen` działa, a w panelu włączone są BLIK, Przelewy24 i karta.

## Faza 1 — Baza danych

- [x] **1.1 Modele i migracja.** Tabele z `docs/ARCHITECTURE.md` w SQLAlchemy 2.0, pierwsza migracja Alembic. Gotowe, gdy: `uv run alembic upgrade head` tworzy pustą bazę.
- [x] **1.2 Dane startowe.** `seed.py` z 4 produktami i 4 kolorami gipsu z makiety. Gotowe, gdy: po seedzie w bazie są produkty z wariantami i stanami.
- [x] **1.3 Testy modeli.** pytest z testową bazą PostgreSQL w Dockerze. Gotowe, gdy: test liczenia sumy zamówienia w groszach przechodzi.

## Faza 2 — API katalogu

- [x] **2.1 Lista produktów.** `GET /api/products?category=` z sortowaniem jak w makiecie. Gotowe, gdy: test zwraca tylko aktywne produkty.
- [x] **2.2 Karta produktu.** `GET /api/products/{slug}` z wariantami i stanem per kolor. Gotowe, gdy: nieistniejący slug zwraca 404.
- [x] **2.3 Ustawienia dostawy.** `GET /api/shipping` (ceny Paczkomatu i kuriera, próg darmowej dostawy). Gotowe, gdy: frontend może z tego policzyć pasek darmowej dostawy.

## Faza 3 — Frontend katalogu

- [x] **3.1 Sklep.** Ekran „Sklep” z makiety na danych z API, filtr kategorii. Gotowe, gdy: działa na 390 px i na komputerze.
- [x] **3.2 Karta produktu.** Wybór koloru gipsu, licznik 1–10, stany „Wyprzedana” i „Ostatnia sztuka”. Gotowe, gdy: przy `stock = 0` przycisk „Dodaj” jest nieaktywny.
- [x] **3.3 Strona główna** i strony prawne (regulamin, polityka prywatności, dostawa i zwroty). Gotowe, gdy: linki w stopce działają.

## Faza 4 — Koszyk

- [x] **4.1 Stan koszyka.** Hook `useCart` z zapisem w `localStorage`. Gotowe, gdy: koszyk przetrwa odświeżenie strony.
- [x] **4.2 Szuflada koszyka** z makiety: zmiana ilości, usuwanie, pasek darmowej dostawy, pusty koszyk. Gotowe, gdy: długie nazwy i 10 sztuk wyglądają dobrze.

## Faza 5 — Checkout ze Stripe (lokalnie)

- [x] **5.1 `POST /api/checkout`.** Walidacja, ceny z bazy, rezerwacja stanu, zapis `pending`, Checkout Session. Gotowe, gdy: test z podstawionym klientem Stripe sprawdza, że cena z requestu jest ignorowana.
- [ ] **5.2 Formularz zamówienia.** Kontakt, Paczkomat (InPost Geowidget) albo adres kuriera, NIP, zgoda. Gotowe, gdy: błędy walidacji wyświetlają się przy polach.
- [ ] **5.3 Przekierowanie i powrót.** Redirect na Stripe, strony `/dziekujemy` i `/zamowienie/anulowane`. Gotowe, gdy: płatność kartą `4242 4242 4242 4242` kończy się na stronie podziękowania.

## Faza 6 — Webhooki i cykl życia zamówienia

- [ ] **6.1 Endpoint webhooka** z weryfikacją podpisu i tabelą `stripe_events`. Gotowe, gdy: `stripe trigger checkout.session.completed` zmienia status, a to samo zdarzenie drugi raz nic nie robi.
- [ ] **6.2 Wygasanie i nieudane płatności** ze zwrotem stanu. Gotowe, gdy: test pokazuje powrót stanu po wygaśnięciu sesji.
- [ ] **6.3 E-maile** dla klienta i dla sprzedawcy (Resend lub SMTP). Gotowe, gdy: po testowej płatności przychodzą oba.
- [ ] **6.4 Status na stronie podziękowania.** `GET /api/orders/by-session/{id}` + odpytywanie co 2 s. Gotowe, gdy: strona pokazuje numer PM-XXXX.

## Faza 7 — Panel administracyjny

- [ ] **7.1 SQLAdmin za hasłem** pod `/admin`: produkty, warianty, stany, ustawienia. Gotowe, gdy: zmiana stanu w panelu jest od razu widoczna w sklepie.
- [ ] **7.2 Obsługa zamówień.** Lista opłaconych, oznaczenie „wysłane” z numerem przesyłki i e-mailem do klienta. Gotowe, gdy: wysłane zamówienie znika z listy „do spakowania”.

## Faza 8 — Wdrożenie

- [ ] **8.1 Domena i DNS w Cloudflare.** Gotowe, gdy: domena wskazuje na Pages, a `api.` (CNAME) na Railway.
- [ ] **8.2 Frontend na Cloudflare Pages** z buildem z `main` i `VITE_API_URL`. Gotowe, gdy: push wdraża stronę w ok. 1 minutę.
- [ ] **8.3 Projekt na Railway:** usługa API (root `backend/`), PostgreSQL, zmienne środowiskowe, usypianie wyłączone, limit wydatków. Gotowe, gdy: `https://api.twojadomena.pl/api/health` zwraca ok.
- [ ] **8.4 Migracje przy wdrożeniu:** `alembic upgrade head` jako pre-deploy. Gotowe, gdy: nowa migracja wchodzi sama po pushu.
- [ ] **8.5 Kopie i monitoring.** Backups na Railway, GitHub Actions z `pg_dump` do R2, UptimeRobot. Gotowe, gdy: baza odtworzona z kopii w lokalnym Dockerze.

## Faza 9 — Testy płatności i start

- [ ] **9.1 Scenariusze testowe** (`/stripe-test`): karta poprawna, 3D Secure, odrzucona, BLIK, Przelewy24, porzucona sesja, powtórzony webhook, dwóch kupujących ostatnią sztukę. Gotowe, gdy: każdy kończy się właściwym statusem i stanem.
- [ ] **9.2 Klucze live**, webhook live, jedno prawdziwe zamówienie i zwrot. Gotowe, gdy: status zmienia się na `refunded`.
- [ ] **9.3 Lista startowa:** regulamin, polityka prywatności, dane sprzedawcy, etykiety CLP, kontakt w sprawie zwrotów.

## Świadomie odłożone

- „Powiadom mnie, gdy wróci” — na start zwykły e-mail do sprzedawcy.
- Etykiety InPost przez API ShipX — na start ręcznie w panelu InPost.
- Kody rabatowe — `allow_promotion_codes` w Checkout, gdy będą potrzebne.
- SSR/SEO, kolejki, Redis, Kubernetes.

## Pomysły na później

(Claude dopisuje tu pomysły spoza zakresu bieżącej historyjki.)

- Pasek ogłoszeń nad nagłówkiem z makiety („Darmowa dostawa od [kwota] zł. Wysyłamy w [X] dni roboczych.”) — kwota z `GET /api/shipping`, najlepiej razem z 3.3 po 2.3.
- Do 6.1: zapis do `stripe_events` i zmiana statusu w jednej transakcji (`INSERT ... ON CONFLICT DO NOTHING` + `rowcount`).
- Do 6.2: zwrot stanu tylko gdy `UPDATE ... WHERE status='pending'` zmienił 1 wiersz, atomowo `stock = stock + qty`, pomiń pozycje z `variant_id IS NULL`. Płatność, która dojdzie po anulowaniu: log + e-mail do sprzedawcy i ręczny zwrot, bez cichego przywracania zamówienia.
- Do 7.1: produkty wyłączamy (`is_active=false`), nie usuwamy (FK `RESTRICT`).
- Newsletter „Nowe zapachy prosto do skrzynki” z makiety strony głównej — wymaga usługi mailingowej i zgody RODO; na razie pominięty.
- Do 9.3: uzupełnić `CONTACT_EMAIL` w `frontend/src/shop.ts`, link do Instagrama, `[miasto]` i `[X] dni` na stronie głównej, treść regulaminu, polityki prywatności oraz dostawy i zwrotów.
- Do 6.x: webhook i e-maile biorą sesję z `app.db.SessionLocal` (w testach podmieniona na bazę testową), nigdy z własnego silnika.
- Do 6.2/7.1: usunięcie wariantu ustawia `order_items.variant_id = NULL`, więc anulowanie zamówienia `pending` nie odda stanu. Rozważ `RESTRICT` na `order_items.variant_id` (nowa migracja) albo tylko dezaktywację wariantów; minimum to obsługa `NULL` w 6.2 z testem.
- Sortowanie „Najnowsze” z makiety Sklep — wymaga daty dodania produktu w API (`created_at` w `products` + migracja).
- Nuty zapachowe „Góra / Serce / Baza” z makiety Produkt — wymagają nowych kolumn w `products` (migracja) i pól w API/panelu.
- Toast „Dodano do koszyka” z linkiem „Koszyk →” (makieta, DESIGN.md) — karta produktu ma na razie tylko „Dodano” na przycisku; link powinien otwierać szufladę (`useCart().open`).
- Szuflada: animacje z makiety, których nie ma w 4.2 — wyjazd pozycji po „Usuń” (`itemOut`), „przewijanie” liczników (`.roll`) i zmiana komunikatu dostawy (`.swap`).
- Do 5.2: `POST /api/checkout` zwraca `detail` jako tekst (422 z naszych reguł, 502, 503), listę błędów Pydantic (422 walidacji pól, `loc` wskazuje pole) albo obiekt `{message, unavailable_variant_ids}` (409); formularz musi obsłużyć wszystkie trzy. Przycisk „Zamawiam i płacę” blokować po kliknięciu (każde kliknięcie to nowe zamówienie i rezerwacja).
- Do 6.2/9.1 (z przeglądu 5.1): limit żądań `POST /api/checkout` (na IP i/lub liczba `pending` na e-mail) — inaczej można zarezerwować cały magazyn na 31 min i powtarzać. Do czasu 6.2 porzucone zamówienia w ogóle nie oddają stanu.
