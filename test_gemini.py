import os
from dotenv import load_dotenv
import requests

load_dotenv(override=True)

api_key = os.getenv("GEMINI_API_KEY")
model = "gemini-flash-latest"
url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

print(f"Testing Gemini with model: {model}")
body = {
    "contents": [{"parts": [{"text": "Hello, are you working?"}]}]
}

try:
    resp = requests.post(url, json=body, timeout=10)
    print(f"Status Code: {resp.status_code}")
    if resp.status_code == 200:
        print("Success!")
        print(resp.json()['candidates'][0]['content']['parts'][0]['text'])
    else:
        print(f"Error: {resp.text}")
except Exception as e:
    print(f"Error: {e}")
