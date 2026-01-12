import requests
import json

def test_endpoints():
    url_reg = "http://127.0.0.1:8080/auth/register"
    url_login = "http://127.0.0.1:8080/auth/login"
    
    headers = {"Content-Type": "application/json"}
    
    reg_data = {
        "email": "diagnostics@copenny.ai",
        "password": "securepassword123",
        "name": "Diagnostic System"
    }
    
    print("Testing /auth/register...")
    try:
        r = requests.post(url_reg, json=reg_data, headers=headers)
        print("Status:", r.status_code)
        print("Response:", r.json())
    except Exception as e:
        print("Registration Request Failed:", e)
        
    login_data = {
        "email": "diagnostics@copenny.ai",
        "password": "securepassword123"
    }
    
    print("\nTesting /auth/login...")
    try:
        r = requests.post(url_login, json=login_data, headers=headers)
        print("Status:", r.status_code)
        print("Response:", r.json())
    except Exception as e:
        print("Login Request Failed:", e)

if __name__ == "__main__":
    test_endpoints()
