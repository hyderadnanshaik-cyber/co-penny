from dotenv import load_dotenv
load_dotenv(override=True)
from fastapi import FastAPI, UploadFile, File, Form, Cookie
from fastapi.responses import FileResponse, RedirectResponse
from fastapi import Response
from fastapi.staticfiles import StaticFiles
from fastapi import Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os, importlib, httpx
import tempfile
import shutil
import json

import sys
import os
# Ensure project root and vectordb are in path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if os.path.join(PROJECT_ROOT, "vectordb") not in sys.path:
    sys.path.insert(0, os.path.join(PROJECT_ROOT, "vectordb"))

from orchestrator import chat as chat_fn
try:
    from enhanced_orchestrator import process_historical_query  # optional
except Exception:
    process_historical_query = None

app = FastAPI(title="Co Penny Advisor")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

from app.routers import alerts
app.include_router(alerts.router)

# Serve minimal static UI (resolve absolute path)
BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__))) # Point to 'app'
STATIC_DIR = os.path.join(BASE_DIR, "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

class ChatReq(BaseModel):
    session_id: str
    message: str
    context: List[Dict[str, str]] = []
    user_id: Optional[str] = None

class CategorizeReq(BaseModel):
    user_id: str
    tx_ids: List[str] = []

class RegisterReq(BaseModel):
    email: str
    password: str
    name: str

class LoginReq(BaseModel):
    email: str
    password: str

class SubscriptionSelectReq(BaseModel):
    user_id: str
    tier: str
    months: int = 1

@app.get("/")
def root():
    return RedirectResponse(url="/landing")

@app.get("/ui")
def ui(copenny_auth: Optional[str] = Cookie(None)):
    print(f"[DEBUG] /ui access - copenny_auth cookie: {copenny_auth}")
    if not copenny_auth:
        print("[DEBUG] Redirecting to landing: unauthorized")
        return RedirectResponse(url="/landing?error=unauthorized")
    index_path = os.path.join(STATIC_DIR, "index.html")
    return FileResponse(index_path)

@app.get("/landing")
def landing():
    landing_path = os.path.join(STATIC_DIR, "landing.html")
    return FileResponse(landing_path)

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/auth/register")
def register(req: RegisterReq, response: Response):
    from database.mongodb_service import get_mongodb_service
    db = get_mongodb_service()
    res = db.register_user(req.email, req.password, req.name)
    if res.get("success") and res.get("user_id"):
        response.set_cookie(key="copenny_auth", value=res["user_id"], path="/", max_age=86400, samesite="lax")
        print(f"[DEBUG] Cookie set for registered user: {res['user_id']}")
    return res

@app.post("/auth/login")
def login(req: LoginReq, response: Response):
    from database.mongodb_service import get_mongodb_service
    db = get_mongodb_service()
    res = db.verify_user(req.email, req.password)
    if res.get("success") and res.get("user_id"):
        response.set_cookie(key="copenny_auth", value=res["user_id"], path="/", max_age=86400, samesite="lax")
        print(f"[DEBUG] Cookie set for logged-in user: {res['user_id']}")
    return res

@app.get("/subscription/status")
def get_subscription_status(user_id: str = Query(...)):
    """Get current subscription status and features for a user"""
    from database.mongodb_service import get_mongodb_service
    db = get_mongodb_service()
    return db.get_user_subscription(user_id)

@app.post("/subscription/select")
def select_subscription(req: SubscriptionSelectReq):
    """Select or upgrade subscription tier"""
    from database.mongodb_service import get_mongodb_service
    db = get_mongodb_service()
    return db.update_user_subscription(req.user_id, req.tier, req.months)

@app.get("/activate-tier")
def activate_tier(user_id: str = Query(...), tier: str = Query("free")):
    """Magic link to instantly switch subscription tiers and redirect to dashboard"""
    from database.mongodb_service import get_mongodb_service
    db = get_mongodb_service()
    tier_lower = tier.lower()
    if tier_lower not in ["free", "pro", "enterprise"]:
        tier_lower = "free"
    db.update_user_subscription(user_id, tier_lower, months=12)
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/ui")

@app.post("/chat")
def chat_api(req: ChatReq):
    try:
        from database.mongodb_service import get_mongodb_service
        db = get_mongodb_service()
        
        # Check subscription limits
        if req.user_id:
            access = db.check_feature_access(req.user_id, "ai_query")
            if not access.get("allowed"):
                return {
                    "answer": "You have reached your AI query limit for today. Please upgrade your plan to continue.",
                    "status": "limit_reached",
                    "type": "error"
                }

        response = chat_fn(req.message, req.context, user_id=req.user_id)
        
        # Increment usage if successful
        if req.user_id and response:
            db.increment_usage(req.user_id, "ai_query")

        if isinstance(response, dict):
            return response
        return {"answer": str(response), "status": "success", "type": "text"}
    except Exception as e:
        return {"answer": f"I apologize, but I encountered an error: {str(e)}", "status": "error", "type": "error"}

@app.delete("/personalization/data")
def delete_user_data(user_id: str = Query(...)):
    """Delete all data associated with a user"""
    from database.mongodb_service import get_mongodb_service
    import shutil
    
    try:
        # Delete from DB
        db = get_mongodb_service()
        db.delete_user_profile(user_id)
        
        # Delete from filesystem
        from app.tools.csv_tools import normalize_user_id
        import stat
        
        def remove_readonly(func, path, excinfo):
            os.chmod(path, stat.S_IWRITE)
            func(path)
            
        safe_id = normalize_user_id(user_id)
        user_dir = os.path.join(PROJECT_ROOT, "state", "models", "user_data", safe_id)
        if os.path.exists(user_dir):
            shutil.rmtree(user_dir, onerror=remove_readonly)
            
        return {"success": True, "message": "User data deleted successfully"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/alerts/history")
def get_alert_history(user_id: str = Query(...), limit: int = Query(50)):
    """Get alert history for a user"""
    from database.mongodb_service import get_mongodb_service
    
    try:
        db = get_mongodb_service()
        alerts = db.get_user_alerts(user_id, limit)
        return {"success": True, "alerts": alerts, "count": len(alerts)}
    except Exception as e:
        return {"success": False, "error": str(e), "alerts": []}

@app.delete("/alerts/history")
def clear_alert_history(user_id: str = Query(...)):
    """Clear all alerts for a user"""
    from database.mongodb_service import get_mongodb_service
    
    try:
        db = get_mongodb_service()
        result = db.clear_user_alerts(user_id)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/dashboard/summary")
def dashboard_summary(user_id: str = Query(...)):
    """Fetch real-time financial metrics for the dashboard"""
    try:
        from app.tools.enhanced_csv_tools import total_spend, category_stats, time_coverage
        from app.tools.csv_tools import normalize_user_id
        
        # Check if user-specific directory exists - sync with PersonalizationEngine
        safe_id = normalize_user_id(user_id)
        user_csv = os.path.join(PROJECT_ROOT, "state", "models", "user_data", safe_id, "transactions.csv")
        active_csv = user_csv if os.path.exists(user_csv) else os.path.join(PROJECT_ROOT, "data", "transactions.csv")
        
        if not os.path.exists(active_csv):
            print(f"[DASHBOARD] CSV not found at: {active_csv}") # Added logging
            return {
                "balance": 0,
                "monthly_expense": 0,
                "confidence": 0,
                "transaction_count": 0,
                "has_data": False
            }
            
        # Get real stats
        ts = total_spend(csv_path=active_csv)
        cats = category_stats(csv_path=active_csv)
        cov = time_coverage(csv_path=active_csv)
        
        # Calculate a pseudo "AI Confidence" based on data density
        import pandas as pd
        df = pd.read_csv(active_csv)
        row_count = len(df)
        
        # Calculate true balance (income - expense)
        total_income = 0
        total_expense = 0
        if 'type' in df.columns:
            total_income = df[df['type'].str.lower() == 'income']['amount'].sum()
            total_expense = df[df['type'].str.lower() == 'expense']['amount'].sum()
        else:
            total_expense = ts.get("total", 0)
            
        balance = total_income - total_expense
        
        confidence = min(99, 50 + (row_count // 10)) if row_count > 0 else 0
        
        return {
            "balance": float(balance),
            "monthly_expense": float(total_expense),
            "confidence": confidence,
            "transaction_count": row_count,
            "date_range": f"{cov.get('min', '...')}-{cov.get('max', '...')}",
            "has_data": True
        }
    except Exception as e:
        print(f"[DASHBOARD ERROR] {str(e)}")
        return {"error": str(e), "has_data": False}

@app.get("/selftest")
def selftest():
    out = {}
    out["csv_exists"] = os.path.exists("data/transactions.csv")
    for m in ["run_expense_categorizer","run_budget_monitor","run_cashflow_predictor","llm.llm_client","llm.schemas","app.tools.categorize","app.tools.budget"]:
        try:
            importlib.import_module(m)
            out[f"import:{m}"] = True
        except Exception as e:
            out[f"import:{m}"] = f"ERR: {e}"
    prov = os.getenv("LLM_PROVIDER","openrouter")
    out["LLM_PROVIDER"] = prov
    if prov == "openrouter":
        out["OPENROUTER_KEY_set"] = bool(os.getenv("OPENROUTER_API_KEY"))
    if prov == "gemini":
        out["GEMINI_KEY_set"] = bool(os.getenv("GEMINI_API_KEY"))
    try:
        from run_budget_monitor import run as rb
        out["budget_smoke"] = rb()
    except Exception as e:
        out["budget_smoke"] = f"ERR: {e}"
    return out


# Flowise-compatible endpoints (minimal)
@app.post("/tools/categorize_txn")
def categorize_txn(req: CategorizeReq):
    from run_expense_categorizer import run as run_cat
    # For demo, ignore tx_ids and run on current CSV
    return run_cat(transactions_path="data/transactions.csv", use_llm=True)

@app.get("/reports/spend_mtd")
def spend_mtd(user_id: str = Query(...)):
    from app.tools.budget import run as budget_run
    return budget_run()

@app.get("/budgets")
def budgets(user_id: str = Query(...)):
    from app.tools.budget import DEFAULT_LIMITS
    return DEFAULT_LIMITS

@app.get("/series/daily_net_flow")
def daily_net_flow(user_id: str = Query(...), window: int = Query(365)):
    # Simple placeholder: return empty series for now (Flowise template stub)
    return []

@app.post("/models/forecast")
def forecast(series: Any):
    from run_cashflow_predictor import run as run_forecast
    return run_forecast()

@app.post("/tools/query_csv")
def http_query_csv(payload: Dict[str, Any]):
    from app.tools.csv_tools import query_csv
    sql = str(payload.get("sql") or "").strip()
    limit = int(payload.get("limit") or 1000)
    return query_csv(sql=sql, limit=limit)

@app.get("/tools/spend_aggregate")
def http_spend_aggregate(month: Optional[str] = Query(None), group_by: str = Query("category")):
    from app.tools.csv_tools import spend_aggregate
    return spend_aggregate(month=month, group_by=group_by)

@app.get("/tools/top_merchants")
def http_top_merchants(month: Optional[str] = Query(None), n: int = Query(10)):
    from app.tools.csv_tools import top_merchants
    return top_merchants(month=month, n=n)

@app.get("/tools/describe_csv")
def http_describe_csv():
    from app.tools.csv_tools import describe_csv
    return describe_csv()

@app.post("/historical/analyze")
def historical_analysis(req: ChatReq):
    """Dedicated endpoint for historical analysis with charts"""
    try:
        response = process_historical_query(req.message, req.context)
        return response
    except Exception as e:
        return {
            "answer": f"Error in historical analysis: {str(e)}",
            "status": "error",
            "type": "error"
        }

@app.get("/historical/years")
def get_available_years():
    """Get list of available years in the dataset"""
    try:
        from app.tools.enhanced_csv_tools import get_available_years
        years = get_available_years()
        return {"years": years, "status": "success"}
    except Exception as e:
        return {"error": str(e), "status": "error"}

@app.get("/historical/year/{year}")
def get_year_data(year: int):
    """Get data for a specific year"""
    try:
        from app.tools.enhanced_csv_tools import extract_year_data
        data = extract_year_data(year)
        return data
    except Exception as e:
        return {"error": str(e), "status": "error"}

@app.get("/historical/range/{start_year}/{end_year}")
def get_year_range_data(start_year: int, end_year: int):
    """Get data for a range of years"""
    try:
        from app.tools.enhanced_csv_tools import extract_year_range_data
        data = extract_year_range_data(start_year, end_year)
        return data
    except Exception as e:
        return {"error": str(e), "status": "error"}


# Personalization endpoints
@app.post("/personalization/upload")
async def upload_personal_data(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    overwrite: bool = Form(False)
):
    """
    Upload personal finance CSV data for personalization
    
    Args:
        file: CSV file with transaction data
        user_id: Unique user identifier
        overwrite: Whether to overwrite existing data
    """
    try:
        from app.tools.personalization import PersonalizationEngine
        from database.mongodb_service import get_mongodb_service
        db = get_mongodb_service()
        
        # Check subscription limits
        access = db.check_feature_access(user_id, "transactions")
        if not access.get("allowed"):
            return {
                "success": False,
                "error": f"You have reached your transaction limit for your current plan ({access.get('limit')} records). Please upgrade to upload more data."
            }

        # Validate file type
        if not file.filename.endswith('.csv'):
            return {
                "success": False,
                "error": "File must be a CSV file"
            }
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            tmp_path = tmp_file.name
        
        try:
            # Process CSV
            engine = PersonalizationEngine()
            result = engine.process_user_csv(tmp_path, user_id, overwrite=overwrite)
            
            # Generate cashflow alerts if upload was successful
            if result.get("success"):
                # Track transaction count based on metadata
                metadata = result.get("metadata", {})
                tx_count = metadata.get("transaction_count", 0)
                # Note: We should ideally increment by tx_count, but for now we just track that they performed an upload
                # In a real production system, we'd count every row.
                db.increment_usage(user_id, "transaction")
                
                generate_cashflow_alerts(user_id, metadata)
            
            return result
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
                
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def generate_cashflow_alerts(user_id: str, metadata: dict):
    """Generate cashflow alerts based on uploaded transaction data"""
    from database.mongodb_service import get_mongodb_service
    import pandas as pd
    
    try:
        db = get_mongodb_service()
        from app.tools.csv_tools import normalize_user_id
        safe_id = normalize_user_id(user_id)
        
        # Load user's CSV data
        user_csv = os.path.join(PROJECT_ROOT, "state", "models", "user_data", safe_id, "transactions.csv")
        if not os.path.exists(user_csv):
            return
        
        df = pd.read_csv(user_csv)
        
        # Detect amount column
        amount_col = None
        for col in df.columns:
            if 'amount' in col.lower() or 'value' in col.lower() or 'sum' in col.lower():
                amount_col = col
                break
        
        if not amount_col:
            return
        
        # Convert to numeric
        df[amount_col] = pd.to_numeric(df[amount_col], errors='coerce')
        
        # Calculate statistics
        avg_amount = df[amount_col].abs().mean()
        max_amount = df[amount_col].abs().max()
        total_expense = df[df[amount_col] < 0][amount_col].sum() if (df[amount_col] < 0).any() else 0
        
        # Alert 1: Large transactions (> 3x average)
        large_threshold = avg_amount * 3
        large_transactions = df[df[amount_col].abs() > large_threshold]
        if len(large_transactions) > 0:
            db.save_cashflow_alert(user_id, {
                "type": "large_transaction",
                "severity": "high",
                "title": "Large Transaction Detected",
                "message": f"Found {len(large_transactions)} transaction(s) exceeding ₹{large_threshold:,.0f}. Largest: ₹{max_amount:,.0f}"
            })
        
        # Alert 2: High expense warning
        if total_expense < -50000:  # expense > 50k
            db.save_cashflow_alert(user_id, {
                "type": "high_expense",
                "severity": "medium",
                "title": "High Expense Warning",
                "message": f"Your total expenses are ₹{abs(total_expense):,.0f}. Consider reviewing your spending."
            })
        
        # Alert 3: Data quality alert
        transaction_count = len(df)
        if transaction_count < 20:
            db.save_cashflow_alert(user_id, {
                "type": "data_quality",
                "severity": "low",
                "title": "Low Data Volume",
                "message": f"Only {transaction_count} transactions uploaded. For better insights, upload more historical data."
            })
        elif transaction_count >= 50:
            db.save_cashflow_alert(user_id, {
                "type": "data_quality", 
                "severity": "low",
                "title": "Good Data Volume",
                "message": f"{transaction_count} transactions analyzed. AI model is ready for accurate predictions."
            })
        
        # Alert 4: Category-based alerts (if category column exists)
        for col in df.columns:
            if 'category' in col.lower() or 'type' in col.lower():
                category_spending = df.groupby(col)[amount_col].sum()
                top_category = category_spending.idxmin()  # Most negative = most spending
                top_amount = abs(category_spending.min())
                if top_amount > avg_amount * 10:
                    db.save_cashflow_alert(user_id, {
                        "type": "category_spending",
                        "severity": "medium",
                        "title": f"High Spending: {top_category}",
                        "message": f"Significant spending of ₹{top_amount:,.0f} detected in {top_category} category."
                    })
                break
                
    except Exception as e:
        print(f"Error generating alerts: {e}")


@app.post("/personalization/train")
def train_personal_model(
    user_id: str = Form(...),
    retrain: bool = Form(False)
):
    """
    Train a personalized model for a user
    
    Args:
        user_id: Unique user identifier
        retrain: Whether to retrain if model already exists
    """
    try:
        from app.tools.personalization import PersonalizationEngine
        
        engine = PersonalizationEngine()
        result = engine.train_user_model(user_id, retrain=retrain)
        return result
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.get("/personalization/status/{user_id}")
def get_personalization_status(user_id: str):
    """
    Get personalization status for a user
    
    Args:
        user_id: Unique user identifier
    """
    try:
        from app.tools.personalization import PersonalizationEngine
        
        engine = PersonalizationEngine()
        
        # Get metadata
        metadata = engine.get_user_metadata(user_id)
        
        # Check if model exists
        model_path = engine.get_user_model_path(user_id)
        has_model = model_path is not None
        
        return {
            "user_id": user_id,
            "has_data": metadata is not None,
            "has_model": has_model,
            "metadata": metadata,
            "model_path": model_path if has_model else None
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.post("/personalization/validate")
async def validate_csv(file: UploadFile = File(...)):
    """
    Validate CSV file structure before upload
    
    Args:
        file: CSV file to validate
    """
    try:
        from app.tools.personalization import PersonalizationEngine
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            tmp_path = tmp_file.name
        
        try:
            engine = PersonalizationEngine()
            result = engine.validate_csv(tmp_path)
            return result
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
                
    except Exception as e:
        return {
            "valid": False,
            "error": str(e)
        }


@app.get("/personalization/users")
def list_personalized_users():
    """List all users with personalized data"""
    try:
        from app.tools.personalization import PersonalizationEngine
        
        engine = PersonalizationEngine()
        users = engine.list_users()
        
        # Get status for each user
        user_statuses = []
        for user_id in users:
            metadata = engine.get_user_metadata(user_id)
            model_path = engine.get_user_model_path(user_id)
            user_statuses.append({
                "user_id": user_id,
                "has_model": model_path is not None,
                "metadata": metadata
            })
        
        return {
            "users": user_statuses,
            "count": len(users)
        }
    except Exception as e:
        return {
            "error": str(e),
            "users": []
        }


# User Profile Management Endpoints (MongoDB)
@app.post("/profile/create")
def create_user_profile(
    user_id: str = Form(...),
    profile_data: str = Form(...)  # JSON string
):
    """
    Create or update user profile in MongoDB
    
    Args:
        user_id: Unique user identifier
        profile_data: JSON string with profile data
    """
    try:
        from database.mongodb_service import get_mongodb_service
        
        mongodb = get_mongodb_service()
        if not mongodb.is_connected():
            return {
                "success": False,
                "error": "MongoDB not connected. Please check your MongoDB setup."
            }
        
        # Parse JSON profile data
        import json
        profile = json.loads(profile_data)
        
        result = mongodb.create_user_profile(user_id, profile)
        return result
    except json.JSONDecodeError:
        return {"success": False, "error": "Invalid JSON in profile_data"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/profile/{user_id}")
def get_user_profile(user_id: str):
    """
    Get user profile from MongoDB
    
    Args:
        user_id: Unique user identifier
    """
    try:
        from database.mongodb_service import get_mongodb_service
        
        mongodb = get_mongodb_service()
        if not mongodb.is_connected():
            # Fallback to file-based profile
            import os
            import json
            profile_path = os.path.join("apex-wealth-agents", "state", "profile.json")
            if os.path.exists(profile_path):
                with open(profile_path, 'r') as f:
                    return {"success": True, "profile": json.load(f), "source": "file"}
            return {"success": False, "error": "Profile not found"}
        
        profile = mongodb.get_user_profile(user_id)
        if profile:
            return {"success": True, "profile": profile, "source": "mongodb"}
        else:
            return {"success": False, "error": "Profile not found"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.put("/profile/{user_id}")
def update_user_profile(
    user_id: str,
    updates: str = Form(...)  # JSON string
):
    """
    Update user profile fields
    
    Args:
        user_id: Unique user identifier
        updates: JSON string with fields to update
    """
    try:
        from database.mongodb_service import get_mongodb_service
        import json
        
        mongodb = get_mongodb_service()
        if not mongodb.is_connected():
            return {
                "success": False,
                "error": "MongoDB not connected"
            }
        
        update_data = json.loads(updates)
        result = mongodb.update_user_profile(user_id, update_data)
        return result
    except json.JSONDecodeError:
        return {"success": False, "error": "Invalid JSON in updates"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.delete("/profile/{user_id}")
def delete_user_profile(user_id: str):
    """
    Delete user profile
    
    Args:
        user_id: Unique user identifier
    """
    try:
        from database.mongodb_service import get_mongodb_service
        
        mongodb = get_mongodb_service()
        if not mongodb.is_connected():
            return {
                "success": False,
                "error": "MongoDB not connected"
            }
        
        result = mongodb.delete_user_profile(user_id)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/profile/list")
def list_all_profiles():
    """List all user profiles"""
    try:
        from database.mongodb_service import get_mongodb_service
        
        mongodb = get_mongodb_service()
        if not mongodb.is_connected():
            return {
                "success": False,
                "error": "MongoDB not connected",
                "users": []
            }
        
        users = mongodb.list_all_users()
        return {
            "success": True,
            "users": users,
            "count": len(users)
        }
    except Exception as e:
        return {"success": False, "error": str(e), "users": []}


@app.get("/database/status")
def database_status():
    """Check MongoDB connection status"""
    try:
        from database.mongodb_service import get_mongodb_service
        
        mongodb = get_mongodb_service()
        is_connected = mongodb.is_connected()
        
        return {
            "mongodb_connected": is_connected,
            "database_name": mongodb.database_name if is_connected else None,
            "status": "connected" if is_connected else "disconnected"
        }
    except Exception as e:
        return {
            "mongodb_connected": False,
            "status": "error",
            "error": str(e)
        }

