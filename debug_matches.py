import uuid
from datetime import datetime
from sqlmodel import Session, create_engine, select
from app.models.match import Match, MatchRead
from app.core.config import settings

# Database setup
DATABASE_URL = "postgresql://postgres:Godisgood@localhost:5432/GoalUp"
engine = create_engine(DATABASE_URL)

def debug_matches():
    with Session(engine) as session:
        try:
            matches = session.exec(select(Match)).all()
            print(f"Found {len(matches)} matches in DB")
            for m in matches:
                try:
                    print(f"Validating match {m.id}")
                    MatchRead.model_validate(m)
                except Exception as e:
                    print(f"Validation FAILED for match {m.id}: {e}")
                    print(f"Match data: {m.model_dump()}")
        except Exception as e:
            print(f"Global error: {e}")

if __name__ == "__main__":
    debug_matches()
