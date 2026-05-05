import requests
try:
    response = requests.post("http://127.0.0.1:8000/generate-plan", json={"rooms": ["living_room"], "edges": []})
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("Success! Image received.")
    else:
        print(f"Error: {response.text}")
except Exception as e:
    print(f"Failed to connect: {e}")
