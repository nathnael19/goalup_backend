import urllib.request
import json

try:
    url = "http://127.0.0.1:8000/api/v1/matches/"
    response = urllib.request.urlopen(url)
    data = json.loads(response.read().decode())
    if data:
        m = data[0]
        print(f"Match ID: {m.get('id')}")
        print(f"Team A: {m.get('team_a')}")
        print(f"Tournament: {m.get('tournament')}")
    else:
        print("No matches found")
except Exception as e:
    print(f"Error: {e}")
