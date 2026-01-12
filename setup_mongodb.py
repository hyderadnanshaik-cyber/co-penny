"""
Quick setup script for MongoDB Atlas connection
Run this script to configure MongoDB connection using your Atlas credentials
"""
import os
import sys

# Add the project to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apex-wealth-agents'))

def setup_mongodb():
    """Setup MongoDB connection with user credentials"""
    
    print("=" * 60)
    print("MongoDB Atlas Connection Setup")
    print("=" * 60)
    print()
    
    # Get credentials from user
    print("Enter your MongoDB Atlas credentials:")
    print("(You can find these in the MongoDB Atlas connection modal)")
    print()
    
    username = input("Username [adnanshaikhyder_db_user]: ").strip()
    if not username:
        username = "adnanshaikhyder_db_userr"
    
    password = input("Password [DrNezBg3XE7nb5bt]: ").strip()
    if not password:
        password = "DrNezBg3XE7nb5bt"
    
    cluster = input("Cluster name [cluster0]: ").strip()
    if not cluster:
        cluster = "cluster0"
    
    database = input("Database name [cashflow]: ").strip()
    if not database:
        database = "cashflow"
    
    print()
    print("Setting up MongoDB connection...")
    
    # Construct connection string
    connection_string = f"mongodb+srv://{username}:{password}@{cluster}.mongodb.net/{database}?retryWrites=true&w=majority"
    
    # Set environment variables
    os.environ["MONGODB_URI"] = connection_string
    os.environ["MONGODB_USERNAME"] = username
    os.environ["MONGODB_PASSWORD"] = password
    os.environ["MONGODB_CLUSTER"] = cluster
    os.environ["MONGODB_DATABASE"] = database
    
    print()
    print("✅ Environment variables set!")
    print()
    print("To make these permanent, add to your system:")
    print()
    print("Windows PowerShell:")
    print(f'  $env:MONGODB_URI = "{connection_string}"')
    print()
    print("Windows Command Prompt:")
    print(f'  setx MONGODB_URI "{connection_string}"')
    print()
    print("Linux/Mac:")
    print(f'  export MONGODB_URI="{connection_string}"')
    print()
    
    # Test connection
    print("Testing MongoDB connection...")
    try:
        import sys
        import os
        # Add apex-wealth-agents to path
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apex-wealth-agents'))
        from database.mongodb_service import get_mongodb_service
        
        mongodb = get_mongodb_service()
        if mongodb.is_connected():
            print("✅ Successfully connected to MongoDB Atlas!")
            print(f"   Database: {database}")
            print(f"   Cluster: {cluster}")
        else:
            print("⚠️  Could not connect to MongoDB")
            print("   Please check your credentials and network access")
    except Exception as e:
        print(f"⚠️  Connection test failed: {e}")
        print("   The credentials are set, but connection test failed.")
        print("   Make sure your IP is whitelisted in MongoDB Atlas Network Access")
    
    print()
    print("=" * 60)
    print("Setup complete! You can now start the application.")
    print("=" * 60)

if __name__ == "__main__":
    setup_mongodb()
