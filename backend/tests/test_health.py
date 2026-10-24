from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.config import Settings
from app.db import get_db
from app.main import app


def test_health_with_db_returns_ok(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


class BrokenSession:
    def execute(self, *args: object, **kwargs: object) -> None:
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))


def test_health_with_db_down_returns_503() -> None:
    def broken_db() -> Iterator[BrokenSession]:
        yield BrokenSession()

    app.dependency_overrides[get_db] = broken_db
    try:
        response = TestClient(app).get("/api/health")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {"detail": "Baza danych niedostępna"}


def test_settings_read_from_env_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("DATABASE_URL=postgresql+psycopg://u:p@db:5432/x\n", encoding="utf-8")

    settings = Settings(_env_file=env_file)

    assert settings.database_url == "postgresql+psycopg://u:p@db:5432/x"
