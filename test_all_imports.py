import sys
import os

sys.path.append(os.getcwd())

try:
    print("Importing app.models.team...")
    from app.models.team import Team
    print("Importing app.models.player...")
    from app.models.player import Player
    print("Importing app.models.match...")
    from app.models.match import Match
    print("Importing app.models.tournament...")
    from app.models.tournament import Tournament
    print("Importing app.models.standing...")
    from app.models.standing import Standing
    
    print("Importing app.main...")
    from app import main
    
    print("SUCCESS: All modules imported.")
except Exception as e:
    print(f"FAILED: {e}")
    import traceback
    traceback.print_exc()
