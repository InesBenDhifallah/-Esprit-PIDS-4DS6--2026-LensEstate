import requests
import json

url = "http://127.0.0.1:8005/generate"
data = {
    "rooms": ["living_room", "kitchen", "bedroom", "bathroom"],
    "edges": [[0, 1], [0, 2], [2, 3]]
}

response = requests.post(url, json=data)
if response.status_code == 200:
    with open("test_api_success.png", "wb") as f:
        f.write(response.content)
    print("Test passed! Image saved as test_api_success.png")
else:
    print(f"Test failed with status {response.status_code}: {response.text}")
