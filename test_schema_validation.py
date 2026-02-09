import sys
import os
import uuid
from datetime import datetime

# Add the current directory to sys.path
sys.path.append(os.getcwd())

from app.models.match import MatchReadDetail, MatchEvent, MatchStats, MatchStatus
from app.models.team import TeamReadWithRoster
from app.models.tournament import TournamentRead

def test_schema_validation():
    print("Testing MatchReadDetail schema validation...")
    
    match_id = uuid.uuid4()
    
    data = {
        "id": match_id,
        "tournament_id": uuid.uuid4(),
        "team_a_id": uuid.uuid4(),
        "team_b_id": uuid.uuid4(),
        "score_a": 1,
        "score_b": 0,
        "status": "finished",
        "start_time": datetime.now(),
        "venue": "Test Venue",
        "events": [],
        "stats": {
            "possession_home": 50, "possession_away": 50,
            "shots_home": 5, "shots_away": 5,
            "shots_on_target_home": 2, "shots_on_target_away": 2,
            "corners_home": 3, "corners_away": 3,
            "fouls_home": 10, "fouls_away": 10
        },
        "tournament": {
            "id": uuid.uuid4(),
            "name": "Test Tournament",
            "year": 2024,
            "type": "Cup"
        },
        "team_a": {
            "id": uuid.uuid4(),
            "name": "Team A",
            "batch": "2024",
            "roster": {"goalkeepers": [], "defenders": [], "midfielders": [], "forwards": []}
        },
        "team_b": {
            "id": uuid.uuid4(),
            "name": "Team B",
            "batch": "2024",
            "roster": {"goalkeepers": [], "defenders": [], "midfielders": [], "forwards": []}
        }
    }
    
    print("Attempting validation...")
    try:
        validated = MatchReadDetail.model_validate(data)
        print("SUCCESS! Validated MatchReadDetail.")
        print(f"Team A Name: {validated.team_a.name}")
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_schema_validation()
