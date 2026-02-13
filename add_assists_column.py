"""
Migration script to add assists column to player table
"""
from sqlalchemy import create_engine, text
from app.core.config import settings

def add_assists_column():
    engine = create_engine(str(settings.DATABASE_URL))
    
    with engine.connect() as conn:
        # Check if column exists
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='player' AND column_name='assists'
        """))
        
        if result.fetchone() is None:
            # Add the column
            conn.execute(text("ALTER TABLE player ADD COLUMN assists INTEGER DEFAULT 0"))
            conn.commit()
            print("✓ Successfully added 'assists' column to player table")
        else:
            print("✓ Column 'assists' already exists")

if __name__ == "__main__":
    add_assists_column()
