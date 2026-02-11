from sqlalchemy import text
from app.core.database import engine

def migrate():
    print("Running migration for news associations...")
    with engine.connect() as conn:
        # Add team_id
        try:
            conn.execute(text('ALTER TABLE "news" ADD COLUMN team_id UUID REFERENCES "team"(id);'))
            print("Successfully added team_id to news table.")
        except Exception as e:
            print(f"Error adding team_id: {e}")
            
        # Add player_id
        try:
            conn.execute(text('ALTER TABLE "news" ADD COLUMN player_id UUID REFERENCES "player"(id);'))
            print("Successfully added player_id to news table.")
        except Exception as e:
            print(f"Error adding player_id: {e}")
            
        conn.commit()

if __name__ == "__main__":
    migrate()
