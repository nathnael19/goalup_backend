from pydantic_settings import BaseSettings
from typing import Optional
from pydantic import validator

class Settings(BaseSettings):
    PROJECT_NAME: str = "GoalUp!"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str
    SUPABASE_PROJECT_URL: str
    SUPABASE_PUBLISHABLE_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_BUCKET_NAME: str = "uploads"
    SECRET_KEY: str
    
    # JWT Settings
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200  # 30 days
    ENVIRONMENT: str = "production" # "development", "production"

    # Email Settings
    MAIL_USERNAME: Optional[str] = None
    MAIL_PASSWORD: Optional[str] = None
    MAIL_FROM: str = "info@goalup.com"
    MAIL_PORT: int = 587
    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_FROM_NAME: str = "GoalUP Admin"
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False
    USE_REAL_MAIL: bool = False

    @validator("MAIL_USERNAME", "MAIL_PASSWORD", pre=True)
    def empty_string_to_none(cls, v):
        if v == "":
            return None
        return v

    class Config:
        import os
        env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")

settings = Settings()
