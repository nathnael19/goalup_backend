from sqlalchemy import text
from app.core.database import engine

def check():
    with engine.connect() as conn:
        # Check team_id
        try:
            conn.execute(text("SELECT team_id FROM news LIMIT 0"))
            print("team_id EXISTS")
        except Exception:
            print("team_id MISSING")
            
        # Check player_id
        try:
            conn.execute(text("SELECT player_id FROM news LIMIT 0"))
            print("player_id EXISTS")
        except Exception:
            print("player_id MISSING")
            
        # Check match_day
        try:
            conn.execute(text('SELECT match_day FROM "match" LIMIT 0'))
            print("match_day EXISTS")
        except Exception:
            print("match_day MISSING")

if __name__ == "__main__":
    check()
