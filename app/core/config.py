from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "GoalUp!"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str
    SUPABASE_PROJECT_URL: str
    SUPABASE_PUBLISHABLE_KEY: str
    SECRET_KEY: str
    
    # JWT Settings
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200  # 30 days

    class Config:
        env_file = ".env"

settings = Settings()
