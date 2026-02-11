import uuid
from sqlalchemy import text
from app.core.database import engine

def migrate_lineups():
    print("Running migration for Advanced Match Lineups...")
    with engine.connect() as conn:
        try:
            # Create lineup table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS "lineup" (
                    id UUID PRIMARY KEY,
                    match_id UUID NOT NULL,
                    team_id UUID NOT NULL,
                    player_id UUID NOT NULL,
                    is_starting BOOLEAN DEFAULT TRUE,
                    CONSTRAINT fk_lineup_match FOREIGN KEY (match_id) REFERENCES "match" (id) ON DELETE CASCADE,
                    CONSTRAINT fk_lineup_team FOREIGN KEY (team_id) REFERENCES "team" (id) ON DELETE CASCADE,
                    CONSTRAINT fk_lineup_player FOREIGN KEY (player_id) REFERENCES "player" (id) ON DELETE CASCADE
                );
            """))
            print("Created lineup table.")
            
        except Exception as e:
            print(f"Error migrating lineups: {e}")
        
        conn.commit()
    print("Migration finished.")

if __name__ == "__main__":
    migrate_lineups()
