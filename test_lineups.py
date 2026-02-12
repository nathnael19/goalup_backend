
import requests
import uuid

BASE_URL = "http://localhost:8000/api/v1"
EMAIL = "testadmin@example.com"
PASSWORD = "testpass123"

def login():
    resp = requests.post(f"{BASE_URL}/auth/login", data={"username": EMAIL, "password": PASSWORD})
    resp.raise_for_status()
    return resp.json()["access_token"]

def test_lineup_replacement():
    token = login()
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Get teams to find players
    print("Getting teams...")
    teams = requests.get(f"{BASE_URL}/teams/", headers=headers).json()
    if len(teams) < 2:
        print("Not enough teams")
        return

    team_a = teams[0]
    team_b = teams[1]
    
    # Get roster
    print(f"Getting roster for {team_a['name']}...")
    team_a_detail = requests.get(f"{BASE_URL}/teams/{team_a['id']}", headers=headers).json()
    roster_a = []
    for cat in ["goalkeepers", "defenders", "midfielders", "forwards"]:
        roster_a.extend(team_a_detail["roster"][cat])
    
    if len(roster_a) < 12:
        print("Not enough players in Team A to test replacement")
        return

    # 2. Create Match
    print("Creating match...")
    tournaments = requests.get(f"{BASE_URL}/tournaments/", headers=headers).json()
    tournament_id = tournaments[0]["id"]
    
    match_data = {
        "tournament_id": tournament_id,
        "team_a_id": team_a["id"],
        "team_b_id": team_b["id"],
        "start_time": "2026-02-12T20:00:00Z",
        "total_time": 90
    }
    match = requests.post(f"{BASE_URL}/matches/", json=match_data, headers=headers).json()
    match_id = match["id"]
    print(f"Match created: {match_id}")

    # 3. Set Initial Lineup (First 11 players)
    initial_players = roster_a[:11]
    payload = []
    for p in initial_players:
        payload.append({
            "match_id": match_id,
            "team_id": team_a["id"],
            "player_id": p["id"],
            "is_starting": True
        })
    
    print("Setting initial lineup...")
    resp = requests.post(f"{BASE_URL}/matches/{match_id}/lineups", json=payload, headers=headers)
    resp.raise_for_status()
    
    # Verify
    lineups = requests.get(f"{BASE_URL}/matches/{match_id}", headers=headers).json()["lineups"]
    print(f"Initial lineup count: {len(lineups)}")
    assert len(lineups) == 11
    
    # 4. Replace Player (Replace P0 with P11)
    print("Replacing player 0 with player 11...")
    replacement_payload = []
    # Add P1 to P10 (Keep)
    for p in initial_players[1:]:
        replacement_payload.append({
            "match_id": match_id,
            "team_id": team_a["id"],
            "player_id": p["id"],
            "is_starting": True
        })
    # Add P11 (New)
    p_new = roster_a[11]
    replacement_payload.append({
        "match_id": match_id,
        "team_id": team_a["id"],
        "player_id": p_new["id"],
        "is_starting": True
    })

    resp = requests.post(f"{BASE_URL}/matches/{match_id}/lineups", json=replacement_payload, headers=headers)
    resp.raise_for_status()
    
    # 5. Verify Replacement
    lineups_updated = requests.get(f"{BASE_URL}/matches/{match_id}", headers=headers).json()["lineups"]
    print(f"Updated lineup count: {len(lineups_updated)}")
    assert len(lineups_updated) == 11
    
    player_ids = [l["player_id"] for l in lineups_updated]
    assert initial_players[0]["id"] not in player_ids
    assert p_new["id"] in player_ids
    print("Replacement verified successfully!")

    # Cleanup
    requests.delete(f"{BASE_URL}/matches/{match_id}", headers=headers)
    print("Match deleted.")

if __name__ == "__main__":
    try:
        test_lineup_replacement()
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
