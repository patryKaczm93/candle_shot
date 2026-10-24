---
name: next-story
description: Realizuje kolejną (albo wskazaną) historyjkę z docs/ROADMAP.md od planu po testy i odhaczenie. Używaj, gdy użytkownik chce przejść do następnego kroku roadmapy.
argument-hint: "[numer historyjki, np. 2.1]"
disable-model-invocation: true
---

Zrealizuj historyjkę z `docs/ROADMAP.md`.

1. Wybór: jeśli podano argument (`$ARGUMENTS`), weź tę historyjkę. W przeciwnym razie pierwszą nieodhaczoną (`- [ ]`) w kolejności faz. Sprawdź, czy poprzednie historyjki, od których zależy, są odhaczone; jeśli nie, powiedz o tym i zapytaj, czy kontynuować.
2. Plan: wypisz w 3–8 punktach, które pliki utworzysz lub zmienisz i jakie testy dodasz. Podaj kryterium „Gotowe, gdy” z roadmapy. Poczekaj na moją akceptację planu.
3. Implementacja: tylko zakres tej historyjki. Trzymaj się zasad z CLAUDE.md i `.claude/rules/`. Pomysły spoza zakresu dopisz do sekcji „Pomysły na później” w ROADMAP zamiast je robić.
4. Weryfikacja: uruchom testy i lint (backend: `uv run pytest`, `uv run ruff check .`; frontend: `npm test`, `npm run lint`). Napraw błędy. Jeśli historyjka dotyka płatności, zamówień lub webhooków, uruchom agenta `payment-reviewer` i popraw zgłoszone problemy.
5. Domknięcie: odhacz historyjkę w `docs/ROADMAP.md` (`- [x]`), pokaż `git status` i zaproponuj wiadomość commita w formacie `feat(<numer>): <opis>`. Nie commituj bez mojej zgody.
6. Na koniec w 2–3 zdaniach: co powstało, jak to sprawdzić ręcznie i jaka jest następna historyjka.
