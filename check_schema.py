from sqlalchemy import text, inspect
from app.core.database import engine

def check_schema():
    inspector = inspect(engine)
    
    for table_name in ["team", "match"]:
        print(f"\nColumns in {table_name}:")
        columns = inspector.get_columns(table_name)
        for column in columns:
            print(f" - {column['name']}: {column['type']}")

if __name__ == "__main__":
    check_schema()
