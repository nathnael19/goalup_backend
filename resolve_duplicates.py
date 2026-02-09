from sqlmodel import Session, select, create_engine, func
from app.models.player import Player
from app.core.config import settings
import uuid

engine = create_engine(settings.DATABASE_URL)
with Session(engine) as session:
    # Find groups of duplicates
    statement = select(Player.team_id, Player.jersey_number, func.count("*")).group_by(Player.team_id, Player.jersey_number).having(func.count("*") > 1)
    duplicates = session.exec(statement).all()
    
    if duplicates:
        print(f"Found {len(duplicates)} groups of duplicates. Resolving...")
        for team_id, jersey, count in duplicates:
            print(f"Resolving Team: {team_id}, Jersey: {jersey}")
            # Find the players in this group
            players = session.exec(
                select(Player)
                .where(Player.team_id == team_id, Player.jersey_number == jersey)
                .order_by(Player.id)
            ).all()
            
            # Keep the first one, update the rest
            # We need to find a free jersey number for each duplicate
            # For simplicity, we'll start from 100 and go up
            new_jersey = 100
            for p in players[1:]:
                # Find a non-conflicting jersey number
                while True:
                    conflict = session.exec(
                        select(Player).where(Player.team_id == team_id, Player.jersey_number == new_jersey)
                    ).first()
                    if not conflict:
                        break
                    new_jersey += 1
                
                print(f"  Updating Player {p.name} ({p.id}) from jersey {p.jersey_number} to {new_jersey}")
                p.jersey_number = new_jersey
                session.add(p)
                new_jersey += 1
        
        session.commit()
        print("Duplicates resolved successfully.")
    else:
        print("No duplicates found.")
