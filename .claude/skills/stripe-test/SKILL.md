---
name: stripe-test
description: Przeprowadza lokalny test integracji Stripe (Checkout + webhooki) według listy scenariuszy z Fazy 9. Używaj po zmianach w checkout, zamówieniach lub webhookach.
disable-model-invocation: true
allowed-tools: Bash(stripe trigger *), Bash(uv run pytest *), Bash(docker compose ps)
---

Przetestuj integrację Stripe lokalnie, w trybie testowym.

Przygotowanie (sprawdź, nie uruchamiaj w tle bez pytania):
- backend działa na :8000, baza działa (`docker compose ps`),
- w osobnym terminalu działa `stripe listen --forward-to localhost:8000/api/webhooks/stripe`, a jego `whsec_...` jest ustawiony jako `STRIPE_WEBHOOK_SECRET` w `backend/.env`. Jeśli nie, poproś mnie o uruchomienie i zatrzymaj się.

1. Testy automatyczne: `uv run pytest -k "checkout or webhook or order"`. Wszystkie muszą przejść.
2. Zdarzenia z CLI: `stripe trigger checkout.session.completed`, `stripe trigger checkout.session.expired`. Sprawdź w logach backendu odpowiedź 200 i brak wyjątków.
3. Scenariusze ręczne — wypisz mi je jako listę do odhaczenia, z kartami testowymi:
   - płatność poprawna: `4242 4242 4242 4242`, dowolna przyszła data, dowolny CVC,
   - 3D Secure: `4000 0027 6000 3184`,
   - karta odrzucona: `4000 0000 0000 0002`,
   - BLIK i Przelewy24 w trybie testowym (Stripe pokazuje stronę testowej autoryzacji),
   - porzucona sesja: zamknij kartę Stripe; po wygaśnięciu stan wraca,
   - powtórzony webhook: „Resend” zdarzenia w panelu Stripe nie zmienia zamówienia drugi raz.
4. Raport: tabela scenariusz → wynik → status zamówienia w bazie → stan magazynu. Zaznacz wszystko, co odbiega od oczekiwań.
