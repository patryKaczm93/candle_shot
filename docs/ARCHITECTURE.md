# Architektura — Pachnie miło

Pełna wersja z diagramem: dokument „Pachnie miło — architektura i roadmapa” w Claude. Ten plik jest skrótem dla pracy w repozytorium.

## Komponenty

| Element | Wybór | Uwagi |
| --- | --- | --- |
| Frontend | React + Vite + TS na Cloudflare Pages (root `frontend/`) | statyczny build z gałęzi `main`, zmienna `VITE_API_URL` |
| API | FastAPI na Railway (root `backend/`) | domena `api.twojadomena.pl`, usypianie WYŁĄCZONE, health check `/api/health` |
| Baza | PostgreSQL na Railway | sieć prywatna Railway, `DATABASE_URL` ze zmiennych; lokalnie Docker |
| Płatności | Stripe Checkout (hostowany) | BLIK, Przelewy24, karta — włączane w panelu Stripe |
| E-maile | Resend albo SMTP | po zmianie statusu na `paid` i `shipped` |
| Kopie | Backups na Railway + cotygodniowy `pg_dump` do Cloudflare R2 (GitHub Actions) | |
| Monitoring | UptimeRobot na `/api/health` co 5 min | |

Przeglądarka → Cloudflare Pages (pliki statyczne). Przeglądarka → API (HTTPS, CORS tylko dla domeny sklepu). API → Stripe (tworzy sesję). Stripe → API (webhook). Przeglądarka → Stripe (przekierowanie) → `/dziekujemy`.

## Przepływ zamówienia

1. Koszyk w `localStorage`: tylko `{variantId, qty}`.
2. `POST /api/checkout`: dane klienta (e-mail, telefon, Paczkomat albo adres, opcjonalnie NIP, zgoda) + pozycje.
3. Backend w jednej transakcji: ceny i stany z bazy, limit 10 szt. na pozycję, koszt dostawy i próg darmowej dostawy z `settings`, zapis `orders` (`pending`) + `order_items` (kopie nazw i cen), rezerwacja `stock`.
4. Checkout Session: `price_data` w PLN w groszach, dostawa jako osobna pozycja, `metadata.order_id`, `client_reference_id`, `customer_email`, `expires_at` = +30 min. Zapis `stripe_session_id`, zwrot `url`.
5. Webhook `POST /api/webhooks/stripe`: podpis → idempotencja (`stripe_events`) → zmiana statusu → 200.
6. `/dziekujemy?session_id=…` odpytuje `GET /api/orders/by-session/{id}` co 2 s i pokazuje numer zamówienia (np. PM-7K3QX9).

| Zdarzenie Stripe | Status | Dodatkowo |
| --- | --- | --- |
| `checkout.session.completed`, `payment_status = paid` | `pending` → `paid` | e-maile, `paid_at` |
| `checkout.session.completed`, `payment_status = unpaid` | bez zmiany | czekamy na zdarzenie asynchroniczne |
| `checkout.session.async_payment_succeeded` | `pending` → `paid` | e-maile, `paid_at` |
| `checkout.session.async_payment_failed` | `pending` → `cancelled` | zwrot rezerwacji |
| `checkout.session.expired` | `pending` → `cancelled` | zwrot rezerwacji |

## Model danych

Kwoty zawsze `int` w groszach.

| Tabela | Kolumny | Uwagi |
| --- | --- | --- |
| `products` | `id`, `slug`, `name`, `tagline`, `description`, `category`, `price_grosze`, `weight_g`, `badge`, `image`, `is_active`, `sort_order` | `slug` w adresie `/sklep/<slug>` |
| `variants` | `id`, `product_id`, `name` (kolor gipsu), `hex`, `stock` | stan per kolor; `stock = 0` → „Ta partia się wypaliła” |
| `orders` | `id`, `number` (losowy kod PM-7K3QX9), `status`, `email`, `phone`, `full_name`, `terms_accepted_at`, `shipping_method` (`locker`/`courier`), `locker_id`, `address_line`, `address_postal_code`, `address_city`, `invoice_nip`, `invoice_name`, `subtotal_grosze`, `shipping_grosze`, `total_grosze`, `stripe_session_id`, `stripe_payment_intent`, `created_at`, `paid_at`, `shipped_at`, `tracking_number` | status: `pending`, `paid`, `shipped`, `cancelled`, `refunded`; numer losowy, żeby nie zdradzał liczby zamówień; `id` nie wychodzi poza backend |
| `order_items` | `order_id`, `variant_id`, `product_name`, `variant_name`, `unit_price_grosze`, `qty` | kopie: zmiana cennika nie zmienia starych zamówień |
| `stripe_events` | `id` (= `event.id`, PK), `type`, `received_at` | idempotencja |
| `settings` | `key`, `value` | ceny dostaw, próg darmowej dostawy |

Zdjęcia produktów w `frontend/public/img/`, w bazie tylko ścieżka.

## Wymagania z makiety

- Warianty: kolor gipsu (naturalny biały, terakota, szałwia, grafit).
- Limit 10 szt. na pozycję; większe zamówienia mailowo.
- Stany: „Dostępna”, „Ostatnia sztuka”, „Wyprzedana”.
- Dostawa: Paczkomat InPost (Geowidget) albo kurier; pasek „Brakuje X zł do darmowej dostawy”.
- Formularz: e-mail, telefon, dostawa, opcjonalna faktura na firmę, zgoda na regulamin.
- Wybór metody płatności odbywa się na stronie Stripe, nie w naszym formularzu.
