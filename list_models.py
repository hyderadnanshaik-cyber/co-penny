import os
from dotenv import load_dotenv
import requests

load_dotenv(override=True)

api_key = os.getenv("GEMINI_API_KEY")
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"

try:
    resp = requests.get(url, timeout=10)
    print(f"Status Code: {resp.status_code}")
    if resp.status_code == 200:
        models = resp.json().get('models', [])
        for m in models:
            print(f"- {m['name']}")
    else:
        print(f"Error: {resp.text}")
except Exception as e:
    print(f"Error: {e}")
