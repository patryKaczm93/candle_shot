---
paths:
  - "backend/app/**/*checkout*.py"
  - "backend/app/**/*webhook*.py"
  - "backend/app/**/*order*.py"
  - "backend/app/**/*stripe*.py"
  - "backend/tests/**/*.py"
---

# Płatności i zamówienia (Stripe Checkout)

Przepływ (szczegóły w docs/ARCHITECTURE.md):

1. `POST /api/checkout` przyjmuje tylko `variant_id` + `qty` i dane klienta. Ceny, które przyśle frontend, są ignorowane.
2. W jednej transakcji: pobierz ceny i stany z bazy, sprawdź limit 10 szt. na pozycję i dostępność, policz dostawę, zapisz `orders` (status `pending`) i `order_items` (kopie nazw i cen), odejmij `stock` (rezerwacja). Użyj `SELECT ... FOR UPDATE` na wariantach.
3. Utwórz Checkout Session: `mode="payment"`, `line_items` z `price_data` w PLN (`unit_amount` w groszach), dostawa jako osobna pozycja, `metadata={"order_id": ...}`, `client_reference_id`, `customer_email`, `expires_at` = teraz + 30 min, `success_url` z `{CHECKOUT_SESSION_ID}`. Metod płatności nie wpisuj w kodzie — włącza się je w panelu Stripe.
4. Webhook `POST /api/webhooks/stripe`:
   - endpoint jako `async def` (jedyny wyjątek od zasady synchronicznych endpointów), czytaj SUROWE body (`await request.body()`), weryfikuj `stripe.Webhook.construct_event(payload, sig_header, settings.stripe_webhook_secret)`; błąd podpisu → 400 bez dotykania bazy,
   - zapisz `event.id` w `stripe_events` (PK); jeśli już istnieje → zwróć 200 i nic nie rób,
   - zmiany statusu zawsze warunkowe: `UPDATE ... WHERE status = 'pending'`,
   - `checkout.session.completed` z `payment_status == "paid"` oraz `checkout.session.async_payment_succeeded` → `paid`,
   - `checkout.session.expired` i `checkout.session.async_payment_failed` → `cancelled` + zwrot rezerwacji do `stock`,
   - e-maile wysyłaj dopiero po commicie transakcji; błąd e-maila nie może zwrócić 500 do Stripe.
5. Strona `/dziekujemy` tylko odczytuje status (`GET /api/orders/by-session/{id}`); nic nie zmienia.

Testy obowiązkowe dla tego kodu: zignorowana cena z requestu, brak stanu, przekroczony limit, poprawny webhook, zły podpis, ten sam event dwa razy, wygaśnięcie sesji zwraca stan, dwóch kupujących ostatnią sztukę. Klienta Stripe w testach podmieniaj (monkeypatch), nie wołaj prawdziwego API.
