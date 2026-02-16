from sqlalchemy import create_engine, text
from app.core.config import settings

def migrate():
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        print("Adding reporter_id column to news table...")
        try:
            conn.execute(text("ALTER TABLE news ADD COLUMN reporter_id INTEGER REFERENCES users(id) ON DELETE SET NULL;"))
            conn.commit()
            print("Migration successful!")
        except Exception as e:
            print(f"Migration failed or column already exists: {e}")

if __name__ == "__main__":
    migrate()
