# Pachnie miło

Sklep z ręcznie robionymi świeczkami. FastAPI + PostgreSQL (Railway), React (Cloudflare Pages), Stripe Checkout.

- Architektura: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- Plan pracy: [docs/ROADMAP.md](docs/ROADMAP.md)
- Design: [docs/design/DESIGN.md](docs/design/DESIGN.md) (zrzuty ekranów, kod makiet, tokeny)

## Wymagania lokalne

- Docker Desktop
- Python 3.12 + [uv](https://docs.astral.sh/uv/)
- Node.js 22 LTS
- [Stripe CLI](https://docs.stripe.com/stripe-cli)

## Uruchomienie

```bash
docker compose up -d db                       # PostgreSQL na :5432

cd backend
cp .env.example .env                          # uzupełnij klucze testowe Stripe
uv sync
uv run alembic upgrade head
uv run python seed.py                         # 4 produkty testowe z makiety
uv run uvicorn app.main:app --reload          # API na :8000

cd ../frontend
cp .env.example .env.local
npm install
npm run dev                                   # sklep na :5173

stripe listen --events checkout.session.completed,checkout.session.async_payment_succeeded,checkout.session.async_payment_failed,checkout.session.expired --forward-to localhost:8000/api/webhooks/stripe
```

### Baza lokalna

- Przed `docker compose up` uruchom Docker Desktop.
- `docker compose ps` pokazuje `healthy`, gdy baza przyjmuje połączenia.
- Kontener ma dwie bazy: `pachnie` (dev) i `pachnie_test` (pytest). Bazę testową tworzy `docker/init-test-db.sql`, ale tylko przy pierwszym utworzeniu wolumenu.
- Reset bazy od zera (kasuje dane): `docker compose down -v && docker compose up -d db`.
- `uv run pytest` używa bazy `pachnie_test` (`TEST_DATABASE_URL`) i przy każdym uruchomieniu odtwarza jej schemat z migracji. Bazy deweloperskiej nie dotyka; odmówi startu, jeśli adres nie wskazuje lokalnej bazy `*_test`. Jeśli testy zgłaszają brak `pachnie_test` (wolumen sprzed skryptu), utwórz ją: `docker compose exec db createdb -U pachnie pachnie_test`.

## Praca z Claude Code

- `CLAUDE.md` — zasady projektu, ładowane w każdej sesji.
- `.claude/rules/` — zasady dla backendu, frontendu, płatności i testów, ładowane przy pracy na pasujących plikach.
- `/next-story` — realizuje kolejną historyjkę z roadmapy.
- `/stripe-test` — lokalny test integracji Stripe.
- Agent `payment-reviewer` — przegląd bezpieczeństwa kodu płatności.

### Stripe lokalnie

- Pracujemy w **sandboxie** Stripe (konto PL, waluta PLN). Metody płatności: Settings → Payments → Payment methods → Cards, BLIK, Przelewy24.
- Stripe CLI na Windows: `scoop bucket add stripe https://github.com/stripe/scoop-stripe-cli.git && scoop install stripe`, potem `stripe login` (wybierz ten sam sandbox).
- `STRIPE_SECRET_KEY` (`sk_test_...`) w `backend/.env`: panel sandboxa → Developers → API keys.
- `STRIPE_WEBHOOK_SECRET` (`whsec_...`) w `backend/.env`: wypisuje go `stripe listen` przy starcie. Jest stały dla danego logowania CLI.
- `stripe listen` wymaga listy zdarzeń (`--events`). Słuchamy tylko czterech zdarzeń Checkout z `docs/ARCHITECTURE.md`.
