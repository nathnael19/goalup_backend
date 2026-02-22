from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)

def run_sql(sql):
    with engine.connect() as conn:
        print(f"Executing: {sql}")
        conn.execute(text(sql))
        conn.commit()

# Add RBAC columns to users table
try:
    print("Updating users table for RBAC...")
    # Add role column
    run_sql("ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(50) DEFAULT 'REFEREE'")
    
    # Add team_id column for Coaches
    run_sql("ALTER TABLE users ADD COLUMN IF NOT EXISTS team_id UUID REFERENCES team(id) ON DELETE SET NULL")
    
    print("Users table updated successfully.")
except Exception as e:
    print(f"Error updating users table: {e}")

print("\nRBAC Migration complete.")
