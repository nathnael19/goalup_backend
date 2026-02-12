import requests
import json
import sys

BASE_URL = "http://127.0.0.1:8000/api/v1"

def verify_matches():
    print("Verifying Matches...")
    try:
        response = requests.get(f"{BASE_URL}/matches/?limit=1")
        if response.status_code != 200:
            print(f"Failed to fetch matches: {response.status_code}")
            return False
        
        matches = response.json()
        if not matches:
            print("No matches found to verify.")
            return True # verifying structure needs data, but empty list is valid response
        
        match = matches[0]
        print("Checking first match structure...")
        
        has_goals = 'goals' in match
        has_cards = 'cards' in match
        has_lineups = 'lineups' in match
        has_subs = 'substitutions' in match
        
        print(f"Has goals: {has_goals}")
        print(f"Has cards: {has_cards}")
        print(f"Has lineups: {has_lineups}")
        print(f"Has substitutions: {has_subs}")
        
        if not (has_goals and has_cards and has_lineups and has_subs):
            print("FAILED: Match response missing enriched fields")
            return False
            
        print("Matches verification PASSED")
        return True
    except Exception as e:
        print(f"Error accessing matches: {e}")
        return False

def verify_teams():
    print("\nVerifying Teams...")
    try:
        # Check if teams endpoint supports limit, otherwise just fetch all (teams usually fewer than matches)
        response = requests.get(f"{BASE_URL}/teams/")
        if response.status_code != 200:
            print(f"Failed to fetch teams: {response.status_code}")
            return False
            
        teams = response.json()
        if not teams:
            print("No teams found to verify.")
            return True
            
        team = teams[0]
        print("Checking first team structure...")
        
        has_tournament = 'tournament' in team
        print(f"Has tournament: {has_tournament}")
        
        if not has_tournament:
            print("FAILED: Team response missing tournament field")
            return False
            
        print("Teams verification PASSED")
        return True
    except Exception as e:
        print(f"Error accessing teams: {e}")
        return False

if __name__ == "__main__":
    m_ok = verify_matches()
    t_ok = verify_teams()
    
    if m_ok and t_ok:
        print("\nALL VERIFICATIONS PASSED")
        sys.exit(0)
    else:
        print("\nVERIFICATION FAILED")
        sys.exit(1)
