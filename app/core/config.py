from pydantic_settings import BaseSettings
from typing import Optional, List
from pydantic import validator

class Settings(BaseSettings):
    PROJECT_NAME: str = "GoalUp!"
    API_V1_STR: str = "/api/v1"

    # Neon Postgres connection strings
    # Primary URL (used by default / in production)
    DATABASE_URL: str
    # Optional overrides for specific environments
    DATABASE_URL_DEV: Optional[str] = None
    DATABASE_URL_TEST: Optional[str] = None

    SUPABASE_PROJECT_URL: str
    SUPABASE_PUBLISHABLE_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_BUCKET_NAME: str = "uploads"

    # Legacy SECRET_KEY — kept for signing custom tokens (invitations, etc.)
    SECRET_KEY: str

    # JWT Settings for custom auth
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # 1 hour
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30   # 30 days
    ENVIRONMENT: str = "production"  # "development", "production"

    # CORS — comma-separated list of allowed origins, e.g. "https://goalup.webcode.codes,http://localhost:5173"
    ALLOWED_ORIGINS: str = "http://localhost:5173,https://goalup.webcode.codes,"

    # Admin frontend URL used in invitation emails
    ADMIN_FRONTEND_URL: str = "https://goalup.webcode.codes"

    @property
    def BACKEND_CORS_ORIGINS(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    # Email Settings
    MAIL_USERNAME: Optional[str] = None
    MAIL_PASSWORD: Optional[str] = None
    MAIL_FROM: Optional[str] = None
    MAIL_PORT: int = 587
    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_FROM_NAME: str = "GoalUP Admin"
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False
    USE_REAL_MAIL: bool = False
    RESEND_API_KEY: Optional[str] = None
    # Optional webhook for push-style notifications (e.g. to another service)
    PUSH_WEBHOOK_URL: Optional[str] = None

    @validator("MAIL_USERNAME", "MAIL_PASSWORD", "MAIL_FROM", pre=True)
    def empty_string_to_none(cls, v):
        if v == "":
            return None
        return v

    @validator("MAIL_FROM")
    def set_mail_from(cls, v, values):
        if v is None:
            return values.get("MAIL_USERNAME")
        return v

    class Config:
        import os
        env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")

settings = Settings()
