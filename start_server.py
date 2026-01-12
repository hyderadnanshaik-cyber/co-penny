#!/usr/bin/env python3
"""
Start the Cashflow server on port 8000
"""
import uvicorn
import os
import sys

# Ensure project root is in path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Load environment before anything else
from dotenv import load_dotenv
load_dotenv(override=True)

if __name__ == "__main__":
    print("Starting Cashflow server...")
    
    # Environment Diagnostics
    provider = os.getenv("LLM_PROVIDER", "free")
    model_env = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
    
    # Mirror the logic in llm_client.py for visibility
    if "2.0" in str(model_env) or "1.5-flash" == model_env:
        model_env = "gemini-flash-latest"
        
    print(f"LLM Configuration: Provider={provider}, Effective Model={model_env}")
    
    print("Landing page: http://localhost:8080/landing")
    print("Chat interface: http://localhost:8080/ui")
    print("API docs: http://localhost:8080/docs")
    print("Health check: http://localhost:8080/health")
    print("\nPress Ctrl+C to stop the server")
    
    port = int(os.environ.get("PORT", 8080))
    print(f"Starting server on port {port}...")
    
    uvicorn.run(
        "app.main:app", 
        host="0.0.0.0", 
        port=port, 
        log_level="info",
        reload=False  # Reload false for production
    )
