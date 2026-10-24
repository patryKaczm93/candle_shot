---
paths:
  - "backend/**/*.py"
---

# Backend (FastAPI)

- Struktura: `app/main.py` (aplikacja, CORS, routery), `app/config.py` (pydantic-settings), `app/db.py` (engine, sesja), `app/models.py`, `app/schemas.py`, `app/routers/<obszar>.py`, `app/services/<obszar>.py`. Nie twórz kolejnych warstw (repozytoria, DI-kontenery), dopóki plik nie przekroczy ~300 linii.
- Logika biznesowa w `services/`, routery tylko walidują wejście i wołają serwis.
- SQLAlchemy 2.0: `Mapped[...]`, `mapped_column`, `select()`. Sesja przez zależność `get_db`. Synchronicznie (`def`), bez async — przy tej skali prostsze i wystarczające.
- Wszystkie ścieżki API pod prefiksem `/api`.
- Wejście i wyjście przez modele Pydantic; nie zwracaj obiektów ORM bezpośrednio.
- Kwoty: kolumny `*_grosze` typu `int`. Formatowanie do „49,00 zł” robi frontend.
- Błędy: `HTTPException` z czytelnym `detail` po polsku, jeśli trafia do klienta.
- Konfiguracja tylko przez `app/config.py`; nie używaj `os.environ` w innych plikach. Każdą nową zmienną dopisz do `backend/.env.example`.
- Typy w każdej sygnaturze funkcji. Ruff musi przechodzić.
