import asyncio
import os
from sqlalchemy import text
from app.core.database import engine

async def run_migration():
    print("Running migrations...")
    with engine.connect() as conn:
        # Add stadium to team
        try:
            conn.execute(text("ALTER TABLE team ADD COLUMN stadium VARCHAR;"))
            print("Added stadium to team table.")
        except Exception as e:
            if "already exists" in str(e):
                print("stadium column already exists in team table.")
            else:
                print(f"Error adding stadium to team: {e}")
        
        # Add columns to match
        match_columns = [
            ("first_half_start", "TIMESTAMP"),
            ("second_half_start", "TIMESTAMP"),
            ("finished_at", "TIMESTAMP")
        ]
        
        for col_name, col_type in match_columns:
            try:
                conn.execute(text(f'ALTER TABLE "match" ADD COLUMN {col_name} {col_type};'))
                print(f"Added {col_name} to match table.")
            except Exception as e:
                if "already exists" in str(e):
                    print(f"{col_name} column already exists in match table.")
                else:
                    print(f"Error adding {col_name} to match: {e}")
        
        conn.commit()
    print("Migration finished.")

if __name__ == "__main__":
    import sqlalchemy
    # SQLModel engine is synchronous by default in this setup, or at least used synchronously in database.py
    # Let's check database.py again... it uses create_engine which is sync.
    
    # Synchronous version
    print("Running synchronous migrations...")
    with engine.connect() as conn:
        # Add stadium to team
        try:
            conn.execute(text("ALTER TABLE team ADD COLUMN stadium VARCHAR;"))
            print("Added stadium to team table.")
        except Exception as e:
            if "already exists" in str(e).lower():
                print("stadium column already exists in team table.")
            else:
                print(f"Error adding stadium to team: {e}")
        
        # Add columns to match
        match_columns = [
            ("first_half_start", "TIMESTAMP"),
            ("second_half_start", "TIMESTAMP"),
            ("finished_at", "TIMESTAMP")
        ]
        
        for col_name, col_type in match_columns:
            try:
                conn.execute(text(f'ALTER TABLE "match" ADD COLUMN {col_name} {col_type};'))
                print(f"Added {col_name} to match table.")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"{col_name} column already exists in match table.")
                else:
                    print(f"Error adding {col_name} to match: {e}")
        
        conn.commit()
    print("Migration finished.")
