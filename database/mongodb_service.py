import os
import pymongo
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

class MongoDBService:
    def __init__(self):
        self.uri = os.getenv("MONGODB_URI")
        self.database_name = os.getenv("MONGODB_DATABASE", "copenny")
        self.client = None
        self.db = None
        self.local_mode = False
        self.local_db_path = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")), "state", "local_db.json")
        
        # Ensure state directory exists
        os.makedirs(os.path.dirname(self.local_db_path), exist_ok=True)
        
        if self.uri:
            try:
                # Reduced timeout to 2000ms for faster fallback
                self.client = pymongo.MongoClient(self.uri, serverSelectionTimeoutMS=2000)
                self.db = self.client[self.database_name]
                # Trigger a connection attempt
                self.client.server_info()
                print("[SUCCESS] Connected to MongoDB Atlas")
            except Exception as e:
                print(f"[ERROR] MongoDB Atlas connection failed: {e}")
                self.setup_local_fallback()
        else:
            self.setup_local_fallback()

    def setup_local_fallback(self):
        print("[INIT] Initializing Local Persistent Storage (local_db.json)")
        self.local_mode = True
        try:
            import mongomock
            self.client = mongomock.MongoClient()
            self.db = self.client[self.database_name]
            self.load_local_data()
            print("[SUCCESS] Local storage initialized successfully")
        except ImportError:
            print("[ERROR] mongomock not found. Local storage will be limited.")
            self.db = None

    def load_local_data(self):
        """Load data from JSON into mongomock"""
        if not os.path.exists(self.local_db_path):
            return
        import json
        try:
            with open(self.local_db_path, "r") as f:
                data = json.load(f)
                for collection_name, docs in data.items():
                    if docs:
                        self.db[collection_name].insert_many(docs)
            print(f"[INFO] Loaded data from {self.local_db_path}")
        except Exception as e:
            print(f"[ERROR] Error loading local data: {e}")

    def save_local_data(self):
        """Save mongomock data back to JSON"""
        if not self.local_mode or not self.db:
            return
        import json
        try:
            data = {}
            collections = ["users", "user_profiles", "user_metadata", "user_subscriptions", "cashflow_alerts", "user_models"]
            for coll in collections:
                data[coll] = list(self.db[coll].find({}, {"_id": 0}))
            
            with open(self.local_db_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[ERROR] Error saving local data: {e}")

    def is_connected(self) -> bool:
        if not self.client:
            return False
        try:
            self.client.server_info()
            return True
        except:
            return False

    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        if self.db is None: return None
        return self._strip_id(self.db.user_profiles.find_one({"user_id": user_id}))

    def create_user_profile(self, user_id: str, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        if self.db is None: return {"success": False, "error": "Database not connected"}
        profile_data["user_id"] = user_id
        try:
            self.db.user_profiles.update_one(
                {"user_id": user_id},
                {"$set": profile_data},
                upsert=True
            )
            self.save_local_data()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def update_user_profile(self, user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        if self.db is None: return {"success": False, "error": "Database not connected"}
        try:
            self.db.user_profiles.update_one(
                {"user_id": user_id},
                {"$set": updates}
            )
            self.save_local_data()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_all_users(self) -> List[str]:
        if self.db is None: return []
        return self.db.user_profiles.distinct("user_id")

    def save_user_csv_metadata(self, user_id: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        if self.db is None: return {"success": False, "error": "Database not connected"}
        try:
            self.db.user_metadata.update_one(
                {"user_id": user_id},
                {"$set": metadata},
                upsert=True
            )
            self.save_local_data()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_user_csv_metadata(self, user_id: str) -> Optional[Dict[str, Any]]:
        if self.db is None: return None
        return self._strip_id(self.db.user_metadata.find_one({"user_id": user_id}))

    def delete_user_profile(self, user_id: str) -> Dict[str, Any]:
        if self.db is None: return {"success": False, "error": "Database not connected"}
        try:
            self.db.user_profiles.delete_one({"user_id": user_id})
            # Also delete related data
            self.db.transactions.delete_many({"user_id": user_id})
            self.save_local_data()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def register_user(self, email: str, password: str, name: str) -> Dict[str, Any]:
        if self.db is None: return {"success": False, "error": "Database not connected"}
        import hashlib
        # Normalize email to lowercase for consistent matching
        email = email.lower().strip()
        pw_hash = hashlib.sha256(password.encode()).hexdigest()
        user_id = email.split('@')[0] + "_" + hashlib.md5(email.encode()).hexdigest()[:4]
        
        try:
            if self.db.users.find_one({"email": email}):
                return {"success": False, "error": "User already exists"}
            
            self.db.users.insert_one({
                "email": email,
                "password_hash": pw_hash,
                "user_id": user_id,
                "name": name
            })
            # Create initial profile
            self.create_user_profile(user_id, {"name": name, "email": email})
            self.save_local_data()
            return {"success": True, "user_id": user_id, "name": name}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _strip_id(self, doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Remove MongoDB _id field to ensure JSON serializability"""
        if doc and "_id" in doc:
            doc.pop("_id")
        return doc

    def verify_user(self, email: str, password: str) -> Dict[str, Any]:
        if self.db is None: return {"success": False, "error": "Database not connected"}
        import hashlib
        # Normalize email to lowercase for consistent matching
        email = email.lower().strip()
        pw_hash = hashlib.sha256(password.encode()).hexdigest()
        
        try:
            user = self.db.users.find_one({"email": email, "password_hash": pw_hash})
            if user:
                return {"success": True, "user_id": user["user_id"], "name": user["name"]}
            return {"success": False, "error": "Invalid email or password"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def save_model_info(self, user_id: str, model_info: Dict[str, Any]) -> Dict[str, Any]:
        if self.db is None: return {"success": False, "error": "Database not connected"}
        try:
            self.db.user_models.update_one(
                {"user_id": user_id},
                {"$set": model_info},
                upsert=True
            )
            self.save_local_data()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def save_cashflow_alert(self, user_id: str, alert: Dict[str, Any]) -> Dict[str, Any]:
        """Save a cashflow alert for a user"""
        if self.db is None: return {"success": False, "error": "Database not connected"}
        from datetime import datetime
        try:
            alert["user_id"] = user_id
            alert["created_at"] = datetime.now().isoformat()
            self.db.cashflow_alerts.insert_one(alert)
            self.save_local_data()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_user_alerts(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get alert history for a user"""
        if self.db is None: return []
        try:
            alerts = list(self.db.cashflow_alerts.find(
                {"user_id": user_id},
                {"_id": 0}
            ).sort("created_at", -1).limit(limit))
            return alerts
        except Exception as e:
            print(f"Error fetching alerts: {e}")
            return []

    def clear_user_alerts(self, user_id: str) -> Dict[str, Any]:
        """Clear all alerts for a user"""
        if self.db is None: return {"success": False, "error": "Database not connected"}
        try:
            result = self.db.cashflow_alerts.delete_many({"user_id": user_id})
            self.save_local_data()
            return {"success": True, "deleted_count": result.deleted_count}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # Subscription tier constants
    SUBSCRIPTION_TIERS = {
        "free": {
            "name": "Free",
            "price": 0,
            "max_transactions": 50,
            "max_ai_queries_per_day": 10,
            "alerts_enabled": False,
            "sms_alerts": False,
            "data_retention_months": 3,
            "priority_support": False
        },
        "pro": {
            "name": "Pro",
            "price": 500,
            "max_transactions": 500,
            "max_ai_queries_per_day": 50,
            "alerts_enabled": True,
            "sms_alerts": False,
            "data_retention_months": 12,
            "priority_support": False
        },
        "enterprise": {
            "name": "Enterprise",
            "price": 900,
            "max_transactions": -1,  # Unlimited
            "max_ai_queries_per_day": -1,  # Unlimited
            "alerts_enabled": True,
            "sms_alerts": True,
            "data_retention_months": -1,  # Unlimited
            "priority_support": True
        }
    }

    def update_user_subscription(self, user_id: str, tier: str, months: int = 1) -> Dict[str, Any]:
        """Update user's subscription tier"""
        if self.db is None: return {"success": False, "error": "Database not connected"}
        from datetime import datetime, timedelta
        
        if tier not in self.SUBSCRIPTION_TIERS:
            return {"success": False, "error": f"Invalid tier: {tier}"}
        
        try:
            expiry = None
            if tier != "free":
                expiry = (datetime.now() + timedelta(days=30 * months)).isoformat()
            
            self.db.user_subscriptions.update_one(
                {"user_id": user_id},
                {"$set": {
                    "user_id": user_id,
                    "tier": tier,
                    "expiry": expiry,
                    "updated_at": datetime.now().isoformat(),
                    "ai_queries_today": 0,
                    "transactions_this_month": 0
                }},
                upsert=True
            )
            self.save_local_data()
            return {"success": True, "tier": tier, "expiry": expiry}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_user_subscription(self, user_id: str) -> Dict[str, Any]:
        """Get user's current subscription"""
        if self.db is None: return {"tier": "free", "features": self.SUBSCRIPTION_TIERS["free"]}
        
        try:
            sub = self.db.user_subscriptions.find_one({"user_id": user_id})
            if not sub:
                return {"tier": "free", "features": self.SUBSCRIPTION_TIERS["free"]}
            
            tier = sub.get("tier", "free")
            
            # Check expiry
            from datetime import datetime
            expiry = sub.get("expiry")
            if expiry and tier != "free":
                if datetime.fromisoformat(expiry) < datetime.now():
                    # Subscription expired, downgrade to free
                    tier = "free"
            
            return {
                "tier": tier,
                "features": self.SUBSCRIPTION_TIERS.get(tier, self.SUBSCRIPTION_TIERS["free"]),
                "expiry": sub.get("expiry"),
                "ai_queries_today": sub.get("ai_queries_today", 0),
                "transactions_this_month": sub.get("transactions_this_month", 0)
            }
        except Exception as e:
            return {"tier": "free", "features": self.SUBSCRIPTION_TIERS["free"], "error": str(e)}

    def check_feature_access(self, user_id: str, feature: str) -> Dict[str, Any]:
        """Check if user has access to a feature based on their tier"""
        sub = self.get_user_subscription(user_id)
        tier = sub.get("tier", "free")
        features = sub.get("features", self.SUBSCRIPTION_TIERS["free"])
        
        if feature == "ai_query":
            limit = features.get("max_ai_queries_per_day", 10)
            used = sub.get("ai_queries_today", 0)
            if limit == -1:  # Unlimited
                return {"allowed": True, "remaining": -1}
            return {"allowed": used < limit, "remaining": max(0, limit - used), "limit": limit}
        
        elif feature == "transactions":
            limit = features.get("max_transactions", 50)
            used = sub.get("transactions_this_month", 0)
            if limit == -1:
                return {"allowed": True, "remaining": -1}
            return {"allowed": used < limit, "remaining": max(0, limit - used), "limit": limit}
        
        elif feature == "alerts":
            return {"allowed": features.get("alerts_enabled", False)}
        
        elif feature == "sms_alerts":
            return {"allowed": features.get("sms_alerts", False)}
        
        return {"allowed": True}

    def increment_usage(self, user_id: str, usage_type: str) -> Dict[str, Any]:
        """Increment usage counter for rate limiting"""
        if self.db is None: return {"success": False}
        
        try:
            if usage_type == "ai_query":
                self.db.user_subscriptions.update_one(
                    {"user_id": user_id},
                    {"$inc": {"ai_queries_today": 1}}
                )
            elif usage_type == "transaction":
                self.db.user_subscriptions.update_one(
                    {"user_id": user_id},
                    {"$inc": {"transactions_this_month": 1}}
                )
            self.save_local_data()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

_service = None

def get_mongodb_service():
    global _service
    if _service is None:
        _service = MongoDBService()
    return _service
