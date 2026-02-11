from sqlalchemy import text
from app.core.database import engine

def migrate():
    print("Running migration for match_day...")
    with engine.connect() as conn:
        try:
            conn.execute(text('ALTER TABLE "match" ADD COLUMN match_day INTEGER DEFAULT 1;'))
            conn.execute(text('CREATE INDEX idx_match_match_day ON "match" (match_day);'))
            print("Successfully added match_day to match table.")
            conn.commit()
        except Exception as e:
            if "already exists" in str(e).lower():
                print("match_day column already exists.")
            else:
                print(f"Error: {e}")

if __name__ == "__main__":
    migrate()
