"""
MongoDB Configuration Helper
"""
import os
from typing import Optional


def get_mongodb_connection_string() -> Optional[str]:
    """
    Get MongoDB connection string from environment or return default Atlas format
    
    Returns:
        MongoDB connection string or None
    """
    # Check for environment variable first
    connection_string = os.getenv("MONGODB_URI")
    
    if connection_string:
        return connection_string
    
    # If no env var, check for individual components
    username = os.getenv("MONGODB_USERNAME")
    password = os.getenv("MONGODB_PASSWORD")
    cluster = os.getenv("MONGODB_CLUSTER", "cluster0")  # Default cluster name
    database = os.getenv("MONGODB_DATABASE", "cashflow")
    
    if username and password:
        # Construct Atlas connection string
        # Format: mongodb+srv://username:password@cluster.mongodb.net/database
        return f"mongodb+srv://{username}:{password}@{cluster}.mongodb.net/{database}?retryWrites=true&w=majority"
    
    return None


def setup_mongodb_env(
    username: str,
    password: str,
    cluster: str = "cluster0",
    database: str = "cashflow"
):
    """
    Helper function to set MongoDB environment variables
    
    Args:
        username: MongoDB username
        password: MongoDB password
        cluster: Cluster name (default: cluster0)
        database: Database name (default: cashflow)
    """
    os.environ["MONGODB_USERNAME"] = username
    os.environ["MONGODB_PASSWORD"] = password
    os.environ["MONGODB_CLUSTER"] = cluster
    os.environ["MONGODB_DATABASE"] = database
    
    # Also set the full connection string
    connection_string = f"mongodb+srv://{username}:{password}@{cluster}.mongodb.net/{database}?retryWrites=true&w=majority"
    os.environ["MONGODB_URI"] = connection_string
    
    print(f"✅ MongoDB environment variables set")
    print(f"   Cluster: {cluster}")
    print(f"   Database: {database}")
    print(f"   Username: {username}")

