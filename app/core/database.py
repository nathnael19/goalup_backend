from sqlmodel import SQLModel, create_engine, Session
from app.core.config import settings


def _get_database_url() -> str:
    """
    Pick a database URL based on ENVIRONMENT.

    - production / default  -> DATABASE_URL
    - development           -> DATABASE_URL_DEV (if set) else DATABASE_URL
    - test                  -> DATABASE_URL_TEST (if set) else DATABASE_URL
    """
    env = (settings.ENVIRONMENT or "production").lower()
    if env == "development" and getattr(settings, "DATABASE_URL_DEV", None):
        return settings.DATABASE_URL_DEV  # type: ignore[return-value]
    if env in {"test", "testing"} and getattr(settings, "DATABASE_URL_TEST", None):
        return settings.DATABASE_URL_TEST  # type: ignore[return-value]
    return settings.DATABASE_URL


# Neon/PgBouncer often works best with simplified connect_args when the URL already contains them.
engine = create_engine(
    _get_database_url(),
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
