from sqlalchemy import text
from app.core.database import engine

def migrate():
    print("Running migration for news associations...")
    with engine.connect() as conn:
        try:
            # Adding team_id and player_id to news table
            conn.execute(text('ALTER TABLE "news" ADD COLUMN team_id UUID REFERENCES "team"(id);'))
            conn.execute(text('ALTER TABLE "news" ADD COLUMN player_id UUID REFERENCES "player"(id);'))
            print("Successfully added team_id and player_id to news table.")
            conn.commit()
        except Exception as e:
            if "already exists" in str(e).lower():
                print("Columns already exist in news table.")
            else:
                print(f"Error: {e}")

if __name__ == "__main__":
    migrate()
