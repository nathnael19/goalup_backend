from sqlalchemy import inspect
from app.core.database import engine

def check_news_schema():
    inspector = inspect(engine)
    if "news" not in inspector.get_table_names():
        print("Table 'news' does not exist!")
        return
    
    print("\nColumns in news:")
    columns = inspector.get_columns("news")
    for column in columns:
        print(f" - {column['name']}: {column['type']}")

if __name__ == "__main__":
    check_news_schema()
