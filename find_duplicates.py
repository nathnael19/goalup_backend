from sqlmodel import Session, select, create_engine, func
from app.models.player import Player
from app.core.config import settings
import uuid

engine = create_engine(settings.DATABASE_URL)
with Session(engine) as session:
    statement = select(Player.team_id, Player.jersey_number, func.count("*")).group_by(Player.team_id, Player.jersey_number).having(func.count("*") > 1)
    duplicates = session.exec(statement).all()
    if duplicates:
        print("Duplicates found:")
        for team_id, jersey, count in duplicates:
            print(f"Team ID: {team_id}, Jersey: {jersey}, Count: {count}")
            # Find the players
            players = session.exec(select(Player).where(Player.team_id == team_id, Player.jersey_number == jersey)).all()
            for p in players:
                print(f"  Player ID: {p.id}, Name: {p.name}")
    else:
        print("No duplicates found.")
