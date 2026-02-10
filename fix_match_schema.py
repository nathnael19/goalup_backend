from sqlalchemy import create_engine, text

# Database setup
DATABASE_URL = "postgresql://postgres:Godisgood@localhost:5432/GoalUp"
engine = create_engine(DATABASE_URL)

def fix_schema():
    with engine.connect() as connection:
        try:
            print("Adding additional_time_first_half...")
            connection.execute(text("ALTER TABLE match ADD COLUMN IF NOT EXISTS additional_time_first_half INTEGER DEFAULT 0 NOT NULL;"))
            
            print("Adding additional_time_second_half...")
            connection.execute(text("ALTER TABLE match ADD COLUMN IF NOT EXISTS additional_time_second_half INTEGER DEFAULT 0 NOT NULL;"))
            
            print("Adding total_time...")
            connection.execute(text("ALTER TABLE match ADD COLUMN IF NOT EXISTS total_time INTEGER DEFAULT 90 NOT NULL;"))
            
            connection.commit()
            print("Schema fix applied successfully!")
        except Exception as e:
            print(f"Error applying schema fix: {e}")

if __name__ == "__main__":
    fix_schema()
