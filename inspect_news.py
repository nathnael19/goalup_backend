from sqlalchemy import text
from app.core.database import engine

def inspect_news():
    with engine.connect() as conn:
        try:
            res = conn.execute(text("SELECT * FROM news LIMIT 0"))
            print(f"Columns: {res.keys()}")
        except Exception as e:
            print(f"Error inspecting news: {e}")

if __name__ == "__main__":
    inspect_news()
