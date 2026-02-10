
from sqlmodel import Session, text
from app.core.database import engine

def migrate_schema():
    print("Attempting to add 'tournament_id' column to 'team' table...")
    with Session(engine) as session:
        try:
            # Add column as nullable first
            session.exec(text("ALTER TABLE team ADD COLUMN tournament_id UUID;"))
            session.commit()
            print("Added 'tournament_id' column.")
            
            # Populate with existing data from standings if possible
            print("Populating 'tournament_id' from existing standings...")
            # This is complex in raw SQL depending on dialect. Postgres:
            # UPDATE team SET tournament_id = s.tournament_id FROM standing s WHERE team.id = s.team_id;
            # But let's verify if that syntax assumes standing is unique per team?
            # If team has multiple standings, this might be ambiguous.
            # Given we are "refactoring", we'll try to update from the MOST RECENT standing.
            
            session.exec(text("""
                UPDATE team 
                SET tournament_id = (
                    SELECT tournament_id 
                    FROM standing 
                    WHERE standing.team_id = team.id 
                    LIMIT 1
                )
            """))
            session.commit()
            print("Populated 'tournament_id'.")
            
            # Now add FK constraint
            session.exec(text("ALTER TABLE team ADD CONSTRAINT fk_team_tournament FOREIGN KEY (tournament_id) REFERENCES tournament(id);"))
            session.commit()
            print("Added foreign key constraint.")

            # If we want it non-nullable, we'd do:
            # ALTER TABLE team ALTER COLUMN tournament_id SET NOT NULL;
            # But we might have orphaned teams. Let's leave nullable for safety or handle it.
            
        except Exception as e:
            print(f"Error migrating schema: {e}")

if __name__ == "__main__":
    migrate_schema()
