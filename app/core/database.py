from sqlmodel import SQLModel, create_engine, Session
from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_size=20,             # Increased for better concurrency with Neon
    max_overflow=10,
    pool_pre_ping=True,       # Crucial for serverless: tests connection before use
    pool_recycle=240,         # Recycles before Neon's 5-min idle timeout
    connect_args={"sslmode": "require"} if "localhost" not in settings.DATABASE_URL else {}
)

def get_session():
    with Session(engine) as session:
        yield session

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
