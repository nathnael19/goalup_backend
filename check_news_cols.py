from sqlalchemy import text
from app.core.database import engine

def check_news():
    with engine.connect() as conn:
        res = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'news'"))
        columns = [r[0] for r in res]
        print(f"News columns: {columns}")

if __name__ == "__main__":
    check_news()
