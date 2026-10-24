---
paths:
  - "backend/tests/**/*.py"
  - "frontend/src/**/*.test.{ts,tsx}"
---

# Testy

- Backend: pytest, testowa baza PostgreSQL z `docker compose` (osobna baza `pachnie_test`), każda funkcja testowa w transakcji wycofywanej po teście. Fabryki danych jako proste funkcje w `tests/factories.py`, bez dodatkowych bibliotek.
- Testy API przez `fastapi.testclient.TestClient`.
- Nazwy: `test_<co>_<warunek>_<oczekiwany_wynik>`, np. `test_checkout_with_tampered_price_uses_db_price`.
- Frontend: Vitest + Testing Library tylko dla logiki (koszyk, formatowanie cen, walidacja formularza). Bez testów snapshotowych.
- Nie goń pokrycia procentowego. Testuj ścieżki pieniędzy i stanu magazynowego dokładnie, resztę rozsądnie.
