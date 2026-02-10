
from sqlmodel import Session, text
from app.core.database import engine

def fix_schema():
    print("Attempting to drop 'batch' column from 'team' table...")
    with Session(engine) as session:
        try:
            session.exec(text("ALTER TABLE team DROP COLUMN batch;"))
            session.commit()
            print("Successfully dropped 'batch' column.")
        except Exception as e:
            print(f"Error dropping column: {e}")
            # Check if column exists first? 
            # Postgres: 
            # SELECT column_name FROM information_schema.columns WHERE table_name='team' and column_name='batch';

if __name__ == "__main__":
    fix_schema()
