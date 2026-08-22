from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "sqlite:///./finpilot.db"
    frontend_url: str = "http://localhost:3000"
    frontend_origin_regex: str = r"^https://finpilot-[a-z0-9-]+-ishita22\.vercel\.app$"
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
    email_provider: str = "resend"
    resend_api_key: str = ""
    email_from: str = "Paymentor <onboarding@resend.dev>"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_app_password: str = ""
    smtp_use_tls: bool = True
    openai_api_key: str = ""
    openai_model: str = "gpt-5.6"
    openai_timeout_seconds: float = 20.0
    openai_max_output_tokens: int = 900
    demo_mode: bool = False
    rate_limit_per_minute: int = 180
    auth_rate_limit_per_minute: int = 12

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
    def backend_origin(self) -> str:
        if self.render_external_hostname:
            return f"https://{self.render_external_hostname}"
        return "http://127.0.0.1:8000"

    @property
    def cookie_samesite(self) -> str:
        return "lax" if self.app_env == "development" else "none"

    @property
    def frontend_origin(self) -> str:
        return self.frontend_url.rstrip("/")

    @property
    def email_configured(self) -> bool:
        provider = self.email_provider.strip().lower()
        if provider == "smtp":
            return bool(
                self.email_from
                and self.smtp_host
                and self.smtp_port
                and self.smtp_username
                and self.smtp_app_password
            )
        if provider == "resend":
            return self.resend_api_key.startswith("re_") and bool(self.email_from)
        return False

    @property
    def openai_configured(self) -> bool:
        return self.openai_api_key.startswith("sk-")

    def production_warnings(self) -> list[str]:
        warnings: list[str] = []
        if self.app_env == "production":
            if self.database_url.startswith("sqlite"):
                warnings.append("Production is using SQLite; configure managed PostgreSQL.")
            if len(self.token_encryption_key) < 32:
                warnings.append("TOKEN_ENCRYPTION_KEY must contain at least 32 characters.")
            if not self.frontend_origin.startswith("https://"):
                warnings.append("FRONTEND_URL must use HTTPS in production.")
        return warnings


@lru_cache
def get_settings() -> Settings:
    return Settings()
