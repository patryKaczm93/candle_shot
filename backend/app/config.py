from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    # Separate database for pytest (created by docker/init-test-db.sql).
    test_database_url: str = "postgresql+psycopg://pachnie:pachnie@localhost:5432/pachnie_test"
    frontend_url: str = "http://localhost:5173"


settings = Settings()
