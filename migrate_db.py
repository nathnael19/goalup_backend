from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)

def run_sql(sql):
    with engine.connect() as conn:
        print(f"Executing: {sql}")
        conn.execute(text(sql))
        conn.commit()

# Add missing columns to tournament
try:
    print("Updating tournament table...")
    run_sql("ALTER TABLE tournament ADD COLUMN IF NOT EXISTS knockout_legs INTEGER DEFAULT 1")
    run_sql("ALTER TABLE tournament ADD COLUMN IF NOT EXISTS has_third_place_match BOOLEAN DEFAULT FALSE")
    run_sql("ALTER TABLE tournament ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    run_sql("ALTER TABLE tournament ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    print("Tournament table updated successfully.")
except Exception as e:
    print(f"Error updating tournament: {e}")

# Add missing columns to match
try:
    print("\nUpdating match table...")
    run_sql("ALTER TABLE match ADD COLUMN IF NOT EXISTS stage VARCHAR")
    run_sql("ALTER TABLE match ADD COLUMN IF NOT EXISTS penalty_score_a INTEGER DEFAULT 0")
    run_sql("ALTER TABLE match ADD COLUMN IF NOT EXISTS penalty_score_b INTEGER DEFAULT 0")
    run_sql("ALTER TABLE match ADD COLUMN IF NOT EXISTS is_extra_time BOOLEAN DEFAULT FALSE")
    run_sql("ALTER TABLE match ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    run_sql("ALTER TABLE match ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    print("Match table updated successfully.")
except Exception as e:
    print(f"Error updating match: {e}")

# Add missing columns to team
try:
    print("\nUpdating team table...")
    run_sql("ALTER TABLE team ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    run_sql("ALTER TABLE team ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    print("Team table updated successfully.")
except Exception as e:
    print(f"Error updating team: {e}")

# Add missing columns to player
try:
    print("\nUpdating player table...")
    run_sql("ALTER TABLE player ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    run_sql("ALTER TABLE player ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    print("Player table updated successfully.")
except Exception as e:
    print(f"Error updating player: {e}")

# Create audit_logs table if missing
try:
    print("\nCreating audit_logs table if missing...")
    run_sql("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id UUID PRIMARY KEY,
        action VARCHAR(255) NOT NULL,
        entity_type VARCHAR(50) NOT NULL,
        entity_id VARCHAR(255) NOT NULL,
        description VARCHAR(500) NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    print("Audit logs table checked/created.")
except Exception as e:
    print(f"Error creating audit_logs: {e}")

print("\nMigration complete.")
