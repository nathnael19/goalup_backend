from sqlmodel import Session, select, create_engine
from app.models.tournament import Tournament
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)

try:
    with Session(engine) as session:
        print("Testing Tournament fetch...")
        tournaments = session.exec(select(Tournament)).all()
        print(f"Success! Found {len(tournaments)} tournaments.")
except Exception as e:
    print(f"Error caught: {type(e).__name__}: {e}")
