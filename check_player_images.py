import uuid
from sqlmodel import Session, create_engine, select
from app.models.player import Player
from app.core.config import settings

def check_players():
    engine = create_engine(settings.DATABASE_URL)
    with Session(engine) as session:
        players = session.exec(select(Player).where(Player.image_url != None)).all()
        print(f"Found {len(players)} players with image_url")
        for p in players:
            print(f"Player: {p.name}, Image URL: {p.image_url}")

if __name__ == "__main__":
    check_players()
