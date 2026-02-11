from sqlalchemy import create_engine, inspect
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
inspector = inspect(engine)

def check_table(table_name):
    if not inspector.has_table(table_name):
        print(f"\n--- Table {table_name} DOES NOT EXIST ---")
        return
    print(f"\n--- Columns in {table_name} ---")
    columns = inspector.get_columns(table_name)
    for column in columns:
        print(f"{column['name']} ({column['type']})")

check_table("tournament")
check_table("match")
check_table("team")
check_table("player")
check_table("news")
check_table("standing")
check_table("lineup")
check_table("auditlog")
check_table("audit_log")
