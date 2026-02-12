from sqlalchemy import text
from app.core.database import engine

def migrate_slot_index():
    print("Adding slot_index to lineup table...")
    with engine.connect() as conn:
        try:
            # PostgreSQL syntax: IF NOT EXISTS for columns requires a bit more effort or PG 9.6+
            # I'll just try to add it and catch if it exists
            conn.execute(text("""
                ALTER TABLE "lineup" 
                ADD COLUMN slot_index INTEGER;
            """))
            print("Added slot_index column.")
        except Exception as e:
            if "already exists" in str(e):
                print("slot_index column already exists.")
            else:
                print(f"Error adding slot_index: {e}")
        
        conn.commit()
    print("Migration finished.")

if __name__ == "__main__":
    migrate_slot_index()
