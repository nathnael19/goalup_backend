from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)

with engine.connect() as conn:
    result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'competition_id'"))
    column = result.fetchone()
    if column:
        print("Column competition_id already exists in users table.")
    else:
        print("Column competition_id does not exist. Adding it...")
        conn.execute(text("ALTER TABLE users ADD COLUMN competition_id UUID REFERENCES competition(id)"))
        conn.commit()
        print("Column competition_id added successfully.")
