from pydantic_settings import BaseSettings

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

    class Config:
        import os
        env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")

settings = Settings()
