from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, make_url, text
from sqlalchemy.orm import Session, sessionmaker

import app.db
from app.config import settings
from app.db import get_db
from app.main import app as fastapi_app

BACKEND_DIR = Path(__file__).resolve().parent.parent

# Same options as app.db.SessionLocal, so tests behave like production code.
SESSION_OPTIONS = {"autoflush": False, "expire_on_commit": False}


def _assert_safe_test_database() -> None:
    """The engine fixture drops the whole schema; refuse anything but a local *_test database."""
    url = make_url(settings.test_database_url)
    if (
        not (url.database or "").endswith("_test")
        or url.host not in ("localhost", "127.0.0.1")
        or url == make_url(settings.database_url)
    ):
        pytest.exit("TEST_DATABASE_URL must point to a local *_test database.", returncode=2)


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    """Test database with a fresh schema built by the real Alembic migrations."""
    _assert_safe_test_database()
    test_engine = create_engine(settings.test_database_url)
    with test_engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
        alembic_config = Config(BACKEND_DIR / "alembic.ini")
        alembic_config.attributes["connection"] = connection
        command.upgrade(alembic_config, "head")
    yield test_engine
    test_engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def no_dev_database(engine: Engine) -> Iterator[None]:
    """Code that opens app.db.SessionLocal directly must never reach the dev database."""
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(app.db, "engine", engine)
        patch.setattr(app.db, "SessionLocal", sessionmaker(bind=engine, **SESSION_OPTIONS))
        yield


@pytest.fixture
def db(engine: Engine) -> Iterator[Session]:
    """Session inside a transaction that is rolled back after each test."""
    with engine.connect() as connection:
        transaction = connection.begin()
        # Commits in tested code only release savepoints; the outer transaction is rolled back.
        session = Session(
            bind=connection, join_transaction_mode="create_savepoint", **SESSION_OPTIONS
        )
        try:
            yield session
        finally:
            session.close()
            transaction.rollback()


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    fastapi_app.dependency_overrides[get_db] = lambda: db
    try:
        yield TestClient(fastapi_app)
    finally:
        fastapi_app.dependency_overrides.clear()
