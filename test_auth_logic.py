import os
import sys
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database.mongodb_service import get_mongodb_service

def test_auth():
    db = get_mongodb_service()
    if not db.is_connected():
        print("Failed to connect to MongoDB")
        return

    email = "test@example.com"
    password = "password123"
    name = "Test User"

    print(f"Registering {email}...")
    reg_res = db.register_user(email, password, name)
    print("Register result:", reg_res)

    print(f"Verifying {email}...")
    ver_res = db.verify_user(email, password)
    print("Verify result:", ver_res)

    if ver_res.get("success"):
        print("Auth test PASSED")
    else:
        print("Auth test FAILED")

if __name__ == "__main__":
    test_auth()
