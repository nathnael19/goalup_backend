import sys
import os

# Add the current directory to sys.path
sys.path.append(os.getcwd())

try:
    print("Attempting to import app.models.match...")
    from app.models.match import MatchReadDetail
    print("Successfully imported MatchReadDetail")
    
    print("Attempting to import app.models.team...")
    from app.models.team import TeamReadDetail
    print("Successfully imported TeamReadDetail")
    
except Exception as e:
    print(f"FAILED: {e}")
    import traceback
    traceback.print_exc()
