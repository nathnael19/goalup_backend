from sqlalchemy import text, inspect
from app.core.database import engine

def check_schema():
    inspector = inspect(engine)
    
    tables = ["match", "goal", "audit_logs"]
    for table in tables:
        if table in inspector.get_table_names():
            print(f"\nTable: {table}")
            columns = inspector.get_columns(table)
            for column in columns:
                print(f"  - {column['name']}: {column['type']}")
        else:
            print(f"\nTable {table} DOES NOT EXIST")

if __name__ == "__main__":
    check_schema()
