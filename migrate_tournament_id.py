from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)

def run_sql(sql):
    with engine.connect() as conn:
        print(f"Executing: {sql}")
        conn.execute(text(sql))
        conn.commit()

# Add tournament_id column to users table
try:
    print("Updating users table with tournament_id...")
    run_sql("ALTER TABLE users ADD COLUMN IF NOT EXISTS tournament_id UUID REFERENCES tournament(id) ON DELETE SET NULL")
    print("Users table updated successfully.")
except Exception as e:
    print(f"Error updating users table: {e}")

print("\nTournament ID Migration complete.")
