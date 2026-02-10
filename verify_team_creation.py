
import urllib.request
import json
import sys

BASE_URL = "http://127.0.0.1:8000/api/v1"

def get_tournaments():
    try:
        with urllib.request.urlopen(f"{BASE_URL}/tournaments/") as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                return data
            else:
                print(f"Failed to get tournaments: {response.status}")
                return []
    except Exception as e:
        print(f"Error getting tournaments: {e}")
        return []

def create_team(tournament_id):
    url = f"{BASE_URL}/teams/"
    data = {
        "name": "DB Vercel Team",
        "tournament_id": tournament_id,
        "color": "#00FF00"
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode(),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                print("Team created successfully!")
                team_data = json.loads(response.read().decode())
                print(f"Created Team: {team_data['name']}")
                print(f"Assigned Tournament ID: {team_data.get('tournament_id')}")
                if team_data.get('tournament_id') == tournament_id:
                    print("SUCCESS: Tournament ID persisted correctly.")
                    return True
                else:
                    print("FAILURE: Tournament ID mismatch.")
                    return False
            else:
                print(f"Failed to create team: {response.status}")
                return False
    except urllib.error.HTTPError as e:
        print(f"HTTP Error creating team: {e.code}")
        print(e.read().decode())
        return False
    except Exception as e:
        print(f"Error creating team: {e}")
        return False

def main():
    print("Fetching tournaments...")
    tournaments = get_tournaments()
    
    if not tournaments:
        print("No tournaments found. Cannot verify team creation.")
        return

    print(f"Found {len(tournaments)} tournaments.")
    tournament_id = tournaments[0]['id']
    print(f"Using tournament ID: {tournament_id}")
    
    print("Attempting to create team...")
    create_team(tournament_id)

if __name__ == "__main__":
    main()
