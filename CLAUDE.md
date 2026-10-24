# Pachnie miło — sklep z ręcznie robionymi świeczkami

Mały e-commerce jednej osoby: kilka–kilkanaście zamówień miesięcznie, do ok. 100 produktów.
Priorytety w tej kolejności: bezpieczeństwo płatności, prosty i czytelny kod, niski koszt.
Nie dodawaj warstw, bibliotek ani usług, których obecny krok nie wymaga.

Architektura i model danych: @docs/ARCHITECTURE.md
Plan pracy (fazy i historyjki): @docs/ROADMAP.md
Design (makieta, system designu, mapa ekranów): `docs/design/DESIGN.md`. Wygląd sklepu ma odpowiadać makiecie; szczegóły w `.claude/rules/frontend.md`.

## Stack

- `backend/` — Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, PostgreSQL, pytest. Menedżer pakietów: uv.
- `frontend/` — React + Vite + TypeScript, React Router, Vitest. Statyczny build.
- Płatności: wyłącznie hostowany Stripe Checkout (BLIK, Przelewy24, karta). Bez Stripe Elements.
- Hosting: backend + PostgreSQL na Railway (root `backend/`), frontend na Cloudflare Pages (root `frontend/`).

## Polecenia

Backend (w `backend/`):
- `uv run uvicorn app.main:app --reload` — serwer dev na :8000
- `uv run pytest` — testy
- `uv run ruff check . && uv run ruff format .` — lint i formatowanie
- `uv run alembic revision --autogenerate -m "opis"` / `uv run alembic upgrade head` — migracje
- `docker compose up -d db` (w katalogu głównym) — lokalny PostgreSQL

Frontend (w `frontend/`):
- `npm run dev` — dev na :5173
- `npm test` — Vitest
- `npm run lint` / `npm run build`

Stripe lokalnie:
- `stripe listen --forward-to localhost:8000/api/webhooks/stripe`
- `stripe trigger checkout.session.completed`

## Zasady, których nie łamiemy

- Frontend nigdy nie decyduje o pieniądzach: cena, stan magazynowy i status zamówienia pochodzą tylko z backendu.
- Kwoty wyłącznie jako `int` w groszach. Nigdy `float`.
- Zamówienie zmienia się na `paid` tylko w handlerze webhooka, po weryfikacji podpisu. Nigdy na podstawie przekierowania z Checkout.
- Sekrety tylko w zmiennych środowiskowych. Nie czytaj, nie wypisuj i nie commituj plików `.env`. Wzór zmiennych: `backend/.env.example`.
- Każda zmiana schematu bazy = migracja Alembic w tym samym commicie.
- Logo i wygląd tylko z makiety (`docs/design/`). Nie wymyślaj nowego logo, palety ani fontów.

## Sposób pracy

- Pracujemy jedną historyjką z `docs/ROADMAP.md` naraz (skrót: `/next-story`). Nie wychodź poza jej zakres; pomysły spoza zakresu zapisz w sekcji „Pomysły na później” w ROADMAP.
- Najpierw krótki plan, potem kod, potem testy. Historyjka jest gotowa, gdy spełnia kryterium „Gotowe, gdy” i testy przechodzą.
- Po zmianach w płatnościach, zamówieniach lub webhookach uruchom agenta `payment-reviewer`.
- Commity małe, wiadomości po angielsku w trybie rozkazującym, z numerem historyjki: `feat(5.1): create checkout session`.
- Nie rób `git push` bez mojej prośby.
- Komunikuj się ze mną po polsku. Kod, nazwy i komentarze w kodzie po angielsku; teksty widoczne dla klienta po polsku.
