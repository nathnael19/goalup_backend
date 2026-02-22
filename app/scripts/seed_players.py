from sqlmodel import Session, select
import uuid
import random

# Import your database and models
from app.core.database import engine
from app.models.team import Team
from app.models.player import Player, PlayerPosition
from app.models.tournament import Tournament

# Common names for fake data
FIRST_NAMES = ["James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph", "Thomas", "Charles", "Daniel", "Matthew", "Anthony", "Mark", "Donald", "Steven", "Paul", "Andrew", "Joshua", "Kenneth", "Kevin", "Brian", "George", "Timothy", "Ronald", "Edward", "Jason", "Jeffrey", "Ryan", "Jacob"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson"]

from sqlalchemy import text

def seed_team_players():
    print("Starting player seed process...")
    
    with Session(engine) as session:
        teams_query = session.execute(text("SELECT id, name FROM team")).fetchall()
        print(f"Found {len(teams_query)} teams.")
        
        # Retroactively fix any previously seeded players missing the string position
        session.execute(text("UPDATE player SET position = player_position_enum::varchar WHERE position IS NULL"))

        players_added = 0
        
        for team in teams_query:
            team_id = team[0]
            team_name = team[1]
            existing_players = session.execute(
                text("SELECT jersey_number FROM player WHERE team_id = :tid"),
                {"tid": team_id}
            ).fetchall()
            
            existing_count = len(existing_players)
            if existing_count >= 11:
                print(f"Team '{team_name}' already has {existing_count} players. Skipping.")
                continue
                
            needed = 11 - existing_count
            print(f"Team '{team_name}' needs {needed} more players. Generating...")
            
            used_jerseys = {p[0] for p in existing_players}
            
            positions = ["gk", "cb", "cb", "lb", "rb", "cm", "cm", "cam", "lw", "rw", "st"]
            pos_index = existing_count % len(positions)
            
            for _ in range(needed):
                jersey = random.randint(1, 99)
                while jersey in used_jerseys:
                    jersey = random.randint(1, 99)
                
                used_jerseys.add(jersey)
                pos = positions[pos_index % len(positions)]
                pos_index += 1
                
                name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
                new_id = str(uuid.uuid4())
                
                session.execute(
                    text("""
                        INSERT INTO player 
                        (id, name, team_id, jersey_number, player_position_enum, position, goals, assists, yellow_cards, red_cards) 
                        VALUES (:id, :name, :tid, :jersey, :pos, :pos_str, 0, 0, 0, 0)
                    """),
                    {
                        "id": new_id,
                        "name": name,
                        "tid": team_id,
                        "jersey": jersey,
                        "pos": pos,
                        "pos_str": pos
                    }
                )
                players_added += 1
                
        session.commit()
        print(f"Successfully added {players_added} new players to the database!")

if __name__ == "__main__":
    seed_team_players()
