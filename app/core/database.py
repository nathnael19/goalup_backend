from sqlmodel import SQLModel, create_engine, Session
from app.core.config import settings

# Neon/PgBouncer often works best with simplified connect_args when the URL already contains them.
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=5,
    pool_pre_ping=True,       # Tests connection before use
    pool_recycle=300          # Recycle connections every 5 minutes
)

def get_session():
    with Session(engine) as session:
        yield session

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
