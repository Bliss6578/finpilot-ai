from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "sqlite:///./finpilot.db"
    frontend_url: str = "http://localhost:3000"
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""
    razorpay_client_id: str = ""
    razorpay_client_secret: str = ""
    razorpay_redirect_uri: str = ""
    razorpay_oauth_mode: str = "test"
    token_encryption_key: str = ""
    session_cookie_name: str = "finpilot_session"
    session_days: int = 30
    render_external_hostname: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def razorpay_configured(self) -> bool:
        return self.razorpay_key_id.startswith("rzp_") and bool(self.razorpay_key_secret)

    @property
    def razorpay_oauth_configured(self) -> bool:
        return bool(self.razorpay_client_id and self.razorpay_client_secret and self.token_encryption_key)

    @property
    def sqlalchemy_database_url(self) -> str:
        """Select psycopg 3 when a host provides a standard PostgreSQL URL."""
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        if self.database_url.startswith("postgres://"):
            return self.database_url.replace("postgres://", "postgresql+psycopg://", 1)
        return self.database_url

    @property
    def effective_razorpay_redirect_uri(self) -> str:
        if self.razorpay_redirect_uri:
            return self.razorpay_redirect_uri
        if self.render_external_hostname:
            return f"https://{self.render_external_hostname}/api/razorpay/oauth/callback"
        return "http://127.0.0.1:8000/api/razorpay/oauth/callback"

    @property
    def cookie_samesite(self) -> str:
        return "lax" if self.app_env == "development" else "none"

    @property
    def frontend_origin(self) -> str:
        return self.frontend_url.rstrip("/")


@lru_cache
def get_settings() -> Settings:
    return Settings()
