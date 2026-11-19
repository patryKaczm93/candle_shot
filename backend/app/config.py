from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    # Separate database for pytest (created by docker/init-test-db.sql).
    test_database_url: str = "postgresql+psycopg://pachnie:pachnie@localhost:5432/pachnie_test"
    frontend_url: str = "http://localhost:5173"
    # Test key (sk_test_...) locally; checkout refuses to start without it.
    stripe_secret_key: str = ""
    # whsec_... from `stripe listen` locally; without it every webhook is rejected.
    stripe_webhook_secret: str = ""
    # Without these the shop still works, but e-mails are skipped with a warning in the log.
    resend_api_key: str = ""
    mail_from: str = ""
    shop_owner_email: str = ""
    # /admin is mounted only when both are strong (see app.admin.admin_enabled).
    admin_password: str = ""
    admin_secret_key: str = ""


settings = Settings()
