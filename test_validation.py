import sys
import os
import uuid
from datetime import datetime

# Add the current directory to sys.path
sys.path.append(os.getcwd())

from app.models.match import Match, MatchStatus, MatchReadDetail, MatchEvent, MatchStats
from app.models.team import Team, TeamReadWithRoster, TeamRoster
from app.models.player import Player
from app.models.tournament import Tournament

def test_population():
    print("Testing MatchReadDetail population...")
    
    # Mock data
    match_id = uuid.uuid4()
    match = Match(
        id=match_id,
        tournament_id=uuid.uuid4(),
        team_a_id=uuid.uuid4(),
        team_b_id=uuid.uuid4(),
        score_a=2,
        score_b=1,
        status=MatchStatus.finished, # Explicitly use Enum
        start_time=datetime.now(),
        venue="Test Arena"
    )
    
    sample_events = [
        MatchEvent(match_id=match_id, minute="12'", player_name="John Doe", team_type="home", event_type="goal")
    ]
    
    sample_stats = MatchStats()
    
    data = match.model_dump()
    # Pydantic model_dump might convert enum to string. Let's ensure it's valid for validation.
    print(f"Dumped status: {data['status']} (type: {type(data['status'])})")
    
    data["events"] = sample_events
    data["stats"] = sample_stats
    data["tournament"] = {"id": match.tournament_id, "name": "Test Tournament", "year": 2024, "type": "Cup"}
    
    roster = {"goalkeepers": [], "defenders": [], "midfielders": [], "forwards": []}
    player = Player(id=uuid.uuid4(), name="Goalie", position="Goalkeeper", team_id=match.team_a_id, jersey_number=1)
    # Use model_dump for the nested player to be safe
    roster["goalkeepers"].append(player.model_dump())
    
    data["team_a"] = {
        "id": match.team_a_id,
        "name": "Team A",
        "batch": "2024",
        "roster": roster
    }
    
    data["team_b"] = {
        "id": match.team_b_id,
        "name": "Team B",
        "batch": "2024",
        "roster": {"goalkeepers": [], "defenders": [], "midfielders": [], "forwards": []}
    }
    
    print("Attempting to validate data against MatchReadDetail...")
    try:
        validated = MatchReadDetail.model_validate(data)
        print("SUCCESS!")
        print(f"Validated match status: {validated.status}")
    except Exception as e:
        print(f"FAILED validation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_population()
