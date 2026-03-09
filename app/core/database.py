from sqlmodel import SQLModel, create_engine, Session
from app.core.config import settings

engine = create_engine(
    settings.SUPABASE_DB_URL,
    pool_size=10,
    max_overflow=5,
    pool_pre_ping=True,       # Tests connection before use
    pool_recycle=300,         # Recycle connections every 5 minutes
    connect_args={"sslmode": "require"}
)

def get_session():
    with Session(engine) as session:
        yield session

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
