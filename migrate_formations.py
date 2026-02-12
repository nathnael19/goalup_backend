from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)

def run_sql(sql):
    with engine.connect() as conn:
        print(f"Executing: {sql}")
        conn.execute(text(sql))
        conn.commit()

# Add missing formation columns to match
try:
    print("\nUpdating match table for formations...")
    run_sql("ALTER TABLE match ADD COLUMN IF NOT EXISTS formation_a VARCHAR DEFAULT '4-3-3'")
    run_sql("ALTER TABLE match ADD COLUMN IF NOT EXISTS formation_b VARCHAR DEFAULT '4-3-3'")
    print("Match table updated with formation columns successfully.")
except Exception as e:
    print(f"Error updating match formations: {e}")

print("\nFormation migration complete.")
