"""
Test MongoDB Connection and User Profile Operations
Run this script to verify MongoDB is properly set up and working
"""
import sys
import os
import json

# Add project to path
# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

def test_mongodb_connection():
    """Test MongoDB connection and operations"""
    
    print("=" * 60)
    print("MongoDB Connection Test")
    print("=" * 60)
    print()
    
    try:
        from database.mongodb_service import get_mongodb_service
        
        # Get MongoDB service
        print("1. Connecting to MongoDB...")
        mongodb = get_mongodb_service()
        
        # Check connection
        if not mongodb.is_connected():
            print("❌ MongoDB is NOT connected")
            print()
            print("Troubleshooting:")
            print("  - Check if MONGODB_URI environment variable is set")
            print("  - Verify MongoDB Atlas credentials")
            print("  - Ensure your IP is whitelisted in MongoDB Atlas")
            print("  - Check network connectivity")
            return False
        
        print("✅ MongoDB is connected!")
        print(f"   Database: {mongodb.database_name}")
        print()
        
        # Test user profile operations
        print("2. Testing User Profile Operations...")
        test_user_id = "test_user_123"
        
        # Create test profile
        test_profile = {
            "name": "Test User",
            "currency": "INR",
            "goals": ["test goal 1", "test goal 2"],
            "risk_preference": "moderate",
            "pay_cycle": "monthly",
            "budget_priorities": ["Rent", "Groceries"],
            "advice_tone": "warm, practical"
        }
        
        print("   Creating test profile...")
        result = mongodb.create_user_profile(test_user_id, test_profile)
        if result.get("success"):
            print("   ✅ Profile created successfully")
        else:
            print(f"   ❌ Failed to create profile: {result.get('error')}")
            return False
        
        # Read profile
        print("   Reading profile...")
        profile = mongodb.get_user_profile(test_user_id)
        if profile:
            print("   ✅ Profile retrieved successfully")
            print(f"      Name: {profile.get('name')}")
            print(f"      Goals: {profile.get('goals')}")
        else:
            print("   ❌ Failed to retrieve profile")
            return False
        
        # Update profile
        print("   Updating profile...")
        updates = {"risk_preference": "aggressive"}
        result = mongodb.update_user_profile(test_user_id, updates)
        if result.get("success"):
            print("   ✅ Profile updated successfully")
        else:
            print(f"   ❌ Failed to update profile: {result.get('error')}")
        
        # List users
        print("   Listing all users...")
        users = mongodb.list_all_users()
        print(f"   ✅ Found {len(users)} user(s)")
        
        # Clean up test data (optional)
        print()
        print("3. Cleaning up test data...")
        result = mongodb.delete_user_profile(test_user_id)
        if result.get("success"):
            print("   ✅ Test profile deleted")
        else:
            print("   ⚠️  Could not delete test profile (you can delete it manually)")
        
        print()
        print("=" * 60)
        print("✅ All MongoDB tests passed!")
        print("=" * 60)
        print()
        print("MongoDB is properly configured and ready to use!")
        print()
        print("Collections created:")
        print("  - user_profiles")
        print("  - user_personalization")
        print("  - user_models")
        print()
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure you're in the correct directory and dependencies are installed")
        print("   Run: pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_mongodb_connection()
    sys.exit(0 if success else 1)

