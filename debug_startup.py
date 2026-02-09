import sys
import os

sys.path.append(os.getcwd())

try:
    print("Attempting to import app.main...")
    from app import main
    print("Successfully imported app.main")
except Exception as e:
    print(f"FAILED: {e}")
    import traceback
    traceback.print_exc()
