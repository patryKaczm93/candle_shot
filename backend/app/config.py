from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    # Separate database for pytest (created by docker/init-test-db.sql).
    test_database_url: str = "postgresql+psycopg://pachnie:pachnie@localhost:5432/pachnie_test"
    frontend_url: str = "http://localhost:5173"
    # Test key (sk_test_...) locally; checkout refuses to start without it.
    stripe_secret_key: str = ""


settings = Settings()
