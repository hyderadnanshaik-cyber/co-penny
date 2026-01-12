"""
Personalization Module: Train user-specific models from CSV data
"""
import os
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import joblib
from datetime import datetime
import json

# Try to import MongoDB service (optional)
try:
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
    from database.mongodb_service import get_mongodb_service
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False
    get_mongodb_service = None


class PersonalizationEngine:
    """
    Handles user-specific model training and personalization
    """
    
    def __init__(self, base_dir: Optional[str] = None):
        """
        Initialize Personalization Engine
        
        Args:
            base_dir: Base directory for storing user models (default: state/models/users/)
        """
        if base_dir is None:
            # Get base directory relative to this file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            base_dir = os.path.join(current_dir, "..", "..", "state", "models", "users")
        
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)
        
        # Create user data directory
        self.user_data_dir = os.path.join(os.path.dirname(base_dir), "user_data")
        os.makedirs(self.user_data_dir, exist_ok=True)
        
        # Initialize MongoDB service if available
        self.mongodb = None
        if MONGODB_AVAILABLE:
            try:
                self.mongodb = get_mongodb_service()
                if not self.mongodb.is_connected():
                    self.mongodb = None
            except Exception as e:
                print(f"MongoDB not available, using file-based storage: {e}")
                self.mongodb = None
    
    def validate_csv(self, csv_path: str) -> Dict[str, Any]:
        """
        Validate CSV file structure and return metadata
        
        Args:
            csv_path: Path to CSV file
            
        Returns:
            Dict with validation results and metadata
        """
        try:
            df = pd.read_csv(csv_path, nrows=100)  # Sample first 100 rows
            
            # Check for required columns
            required_cols = []
            date_cols = ['date', 'Date', 'DATE', 'ts', 'timestamp']
            amount_cols = ['amount', 'Amount', 'AMOUNT', 'monthly_expense_total', 'expense']
            category_cols = ['category', 'Category', 'CATEGORY']
            
            date_col = next((c for c in date_cols if c in df.columns), None)
            amount_col = next((c for c in amount_cols if c in df.columns), None)
            category_col = next((c for c in category_cols if c in df.columns), None)
            
            missing = []
            if not date_col:
                missing.append("date column (date/Date/DATE/ts/timestamp)")
            if not amount_col:
                missing.append("amount column (amount/Amount/AMOUNT/expense)")
            
            if missing:
                return {
                    "valid": False,
                    "error": f"Missing required columns: {', '.join(missing)}",
                    "columns": list(df.columns)
                }
            
            # Check data types
            try:
                pd.to_datetime(df[date_col], errors='raise')
            except:
                return {
                    "valid": False,
                    "error": f"Date column '{date_col}' cannot be parsed as dates",
                    "columns": list(df.columns)
                }
            
            try:
                pd.to_numeric(df[amount_col], errors='raise')
            except:
                return {
                    "valid": False,
                    "error": f"Amount column '{amount_col}' cannot be parsed as numbers",
                    "columns": list(df.columns)
                }
            
            # Get full row count
            full_df = pd.read_csv(csv_path)
            total_rows = len(full_df)
            
            return {
                "valid": True,
                "columns": list(df.columns),
                "date_column": date_col,
                "amount_column": amount_col,
                "category_column": category_col,
                "total_rows": total_rows,
                "sample_rows": len(df)
            }
            
        except Exception as e:
            return {
                "valid": False,
                "error": str(e),
                "columns": []
            }
    
    def process_user_csv(
        self,
        csv_path: str,
        user_id: str,
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        Process and store user CSV data
        
        Args:
            csv_path: Path to uploaded CSV file (or Excel file)
            user_id: Unique user identifier
            overwrite: Whether to overwrite existing user data
            
        Returns:
            Dict with processing results
        """
        try:
            # Handle Excel files by converting to CSV first
            if csv_path.lower().endswith(('.xls', '.xlsx')):
                try:
                    df = pd.read_excel(csv_path)
                    # Create a temporary CSV file
                    import tempfile
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp_csv:
                        df.to_csv(tmp_csv.name, index=False)
                        csv_path = tmp_csv.name
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"Failed to convert Excel file: {str(e)}"
                    }

            # Validate CSV
            validation = self.validate_csv(csv_path)
            if not validation["valid"]:
                return {
                    "success": False,
                    "error": validation.get("error", "CSV validation failed")
                }
            
            # Create user directory
            from app.tools.csv_tools import normalize_user_id
            safe_id = normalize_user_id(user_id)
            user_dir = os.path.join(self.user_data_dir, safe_id)
            
            # Robust directory creation to handle potential WinError 5
            try:
                os.makedirs(user_dir, exist_ok=True)
            except OSError as e:
                if e.winerror == 5: # Access Denied usually means something is temporary locking it
                     import time
                     time.sleep(0.5)
                     os.makedirs(user_dir, exist_ok=True)
                else:
                     raise
            
            # Save CSV
            user_csv_path = os.path.join(user_dir, "transactions.csv")
            if os.path.exists(user_csv_path) and not overwrite:
                return {
                    "success": False,
                    "error": f"User data already exists. Use overwrite=True to replace."
                }
            
            # Copy CSV to user directory
            import shutil
            shutil.copy2(csv_path, user_csv_path)
            
            # Load and process data
            df = pd.read_csv(user_csv_path)
            date_col = validation["date_column"]
            amount_col = validation["amount_column"]
            category_col = validation.get("category_column")
            
            # Convert date
            df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
            df[amount_col] = pd.to_numeric(df[amount_col], errors='coerce')
            
            # Calculate statistics
            total_transactions = len(df)
            date_range = {
                "start": str(df[date_col].min().date()) if df[date_col].notna().any() else None,
                "end": str(df[date_col].max().date()) if df[date_col].notna().any() else None
            }
            total_amount = float(df[amount_col].sum())
            
            # Category breakdown if available
            categories = {}
            if category_col:
                category_breakdown = df.groupby(category_col)[amount_col].sum().to_dict()
                categories = {str(k): float(v) for k, v in category_breakdown.items()}
            
            # Save metadata
            metadata = {
                "user_id": user_id,
                "upload_date": datetime.now().isoformat(),
                "total_transactions": total_transactions,
                "date_range": date_range,
                "total_amount": total_amount,
                "categories": categories,
                "columns": validation["columns"]
            }
            
            # Save to MongoDB if available, otherwise use file system
            if self.mongodb and self.mongodb.is_connected():
                self.mongodb.save_user_csv_metadata(user_id, metadata)
            else:
                # Fallback to file system
                metadata_path = os.path.join(user_dir, "metadata.json")
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
            
            return {
                "success": True,
                "user_id": user_id,
                "metadata": metadata,
                "message": f"Successfully processed {total_transactions} transactions"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def extract_features(self, df: pd.DataFrame, date_col: str, amount_col: str, category_col: Optional[str]) -> pd.DataFrame:
        """
        Extract features from transaction data for model training
        
        Args:
            df: DataFrame with transaction data
            date_col: Name of date column
            amount_col: Name of amount column
            category_col: Name of category column (optional)
            
        Returns:
            DataFrame with extracted features
        """
        features = pd.DataFrame()
        
        # Date-based features
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        features['year'] = df[date_col].dt.year
        features['month'] = df[date_col].dt.month
        features['day_of_week'] = df[date_col].dt.dayofweek
        features['day_of_month'] = df[date_col].dt.day
        
        # Amount features
        features['amount'] = pd.to_numeric(df[amount_col], errors='coerce').fillna(0)
        features['amount_log'] = np.log1p(features['amount'].abs())
        features['is_negative'] = (features['amount'] < 0).astype(int)
        
        # Rolling statistics (monthly)
        df_sorted = df.sort_values(date_col)
        monthly_stats = df_sorted.groupby([df_sorted[date_col].dt.year, df_sorted[date_col].dt.month])[amount_col].agg([
            'mean', 'std', 'sum', 'count'
        ]).reset_index()
        monthly_stats.columns = ['year', 'month', 'monthly_mean', 'monthly_std', 'monthly_sum', 'monthly_count']
        
        # Merge monthly stats
        df_sorted['year'] = df_sorted[date_col].dt.year
        df_sorted['month'] = df_sorted[date_col].dt.month
        df_sorted = df_sorted.merge(monthly_stats, on=['year', 'month'], how='left')
        
        features['monthly_mean'] = df_sorted['monthly_mean'].fillna(0)
        features['monthly_std'] = df_sorted['monthly_std'].fillna(0)
        features['monthly_sum'] = df_sorted['monthly_sum'].fillna(0)
        features['monthly_count'] = df_sorted['monthly_count'].fillna(0)
        
        # Category encoding if available
        if category_col and category_col in df.columns:
            # One-hot encode top categories
            top_categories = df[category_col].value_counts().head(10).index.tolist()
            for cat in top_categories:
                features[f'category_{cat}'] = (df[category_col] == cat).astype(int)
        
        # Fill NaN values
        features = features.fillna(0)
        
        return features
    
    def create_labels(self, df: pd.DataFrame, amount_col: str) -> pd.Series:
        """
        Create labels for financial health prediction
        
        Args:
            df: DataFrame with transaction data
            amount_col: Name of amount column
            
        Returns:
            Series with labels (Good/At Risk/Bad)
        """
        amounts = pd.to_numeric(df[amount_col], errors='coerce').fillna(0)
        
        # Calculate monthly surplus (income - expenses)
        # Assume positive amounts are income, negative are expenses
        monthly_data = df.groupby([df['date'].dt.year, df['date'].dt.month])[amount_col].sum()
        
        labels = []
        for idx, row in df.iterrows():
            year = row['date'].year
            month = row['date'].month
            
            monthly_total = monthly_data.get((year, month), 0)
            
            # Simple rule-based labeling
            if monthly_total < 0:
                label = "Bad"
            elif monthly_total < abs(monthly_total) * 0.2:  # Less than 20% surplus
                label = "At Risk"
            else:
                label = "Good"
            
            labels.append(label)
        
        return pd.Series(labels, index=df.index)
    
    def train_user_model(
        self,
        user_id: str,
        retrain: bool = False
    ) -> Dict[str, Any]:
        """
        Train a personalized model for a user
        
        Args:
            user_id: Unique user identifier
            retrain: Whether to retrain if model already exists
            
        Returns:
            Dict with training results
        """
        try:
            from app.tools.csv_tools import normalize_user_id
            safe_id = normalize_user_id(user_id)
            user_dir = os.path.join(self.user_data_dir, safe_id)
            user_csv_path = os.path.join(user_dir, "transactions.csv")
            
            if not os.path.exists(user_csv_path):
                return {
                    "success": False,
                    "error": f"No data found for user {user_id}. Please upload CSV first."
                }
            
            # Check if model already exists
            from app.tools.csv_tools import normalize_user_id
            safe_id = normalize_user_id(user_id)
            model_path = os.path.join(self.base_dir, f"{safe_id}_model.pkl")
            if os.path.exists(model_path) and not retrain:
                return {
                    "success": True,
                    "message": f"Model already exists for user {user_id}",
                    "model_path": model_path,
                    "retrained": False
                }
            
            # Load user data
            df = pd.read_csv(user_csv_path)
            
            # Load metadata to get column names
            metadata_path = os.path.join(user_dir, "metadata.json")
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                date_col = metadata.get("columns", [])
                # Find date and amount columns
                date_col = next((c for c in ['date', 'Date', 'DATE', 'ts', 'timestamp'] if c in df.columns), None)
                amount_col = next((c for c in ['amount', 'Amount', 'AMOUNT', 'monthly_expense_total', 'expense'] if c in df.columns), None)
                category_col = next((c for c in ['category', 'Category', 'CATEGORY'] if c in df.columns), None)
            else:
                # Fallback detection
                date_col = next((c for c in ['date', 'Date', 'DATE', 'ts', 'timestamp'] if c in df.columns), None)
                amount_col = next((c for c in ['amount', 'Amount', 'AMOUNT', 'monthly_expense_total', 'expense'] if c in df.columns), None)
                category_col = next((c for c in ['category', 'Category', 'CATEGORY'] if c in df.columns), None)
            
            if not date_col or not amount_col:
                return {
                    "success": False,
                    "error": "Could not detect required date and amount columns"
                }
            
            # Convert date
            df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
            df = df.dropna(subset=[date_col, amount_col])
            
            if len(df) < 10:
                return {
                    "success": False,
                    "error": f"Insufficient data: need at least 10 transactions, found {len(df)}"
                }
            
            # Extract features
            features_df = self.extract_features(df, date_col, amount_col, category_col)
            
            # Create labels (simplified - using rule-based approach)
            # For better personalization, we'll predict financial health based on patterns
            amounts = pd.to_numeric(df[amount_col], errors='coerce')
            
            # Calculate monthly aggregates
            df['year'] = df[date_col].dt.year
            df['month'] = df[date_col].dt.month
            monthly_totals = df.groupby(['year', 'month'])[amount_col].sum()
            
            # Create labels based on monthly patterns
            labels = []
            for idx, row in df.iterrows():
                year = row['year']
                month = row['month']
                monthly_total = monthly_totals.get((year, month), 0)
                
                # Normalize by user's average
                user_avg = amounts.abs().mean()
                if user_avg == 0:
                    label = "Good"
                else:
                    ratio = abs(monthly_total) / user_avg
                    if monthly_total < -user_avg * 1.5:  # Spending > 1.5x average
                        label = "Bad"
                    elif monthly_total < -user_avg * 0.8:  # Spending > 0.8x average
                        label = "At Risk"
                    else:
                        label = "Good"
                
                labels.append(label)
            
            labels_series = pd.Series(labels, index=df.index)
            
            # Prepare training data
            X = features_df.values
            y = labels_series.values
            
            # Split data
            if len(X) < 20:
                X_train, X_test = X, X
                y_train, y_test = y, y
            else:
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y, test_size=0.2, random_state=42, stratify=y if len(set(y)) > 1 else None
                )
            
            # Train model
            model = RandomForestClassifier(n_estimators=100, random_state=42, max_depth=10)
            model.fit(X_train, y_train)
            
            # Calculate accuracy
            train_score = model.score(X_train, y_train)
            test_score = model.score(X_test, y_test) if len(X_test) > 0 else train_score
            
            # Save model
            os.makedirs(os.path.dirname(model_path), exist_ok=True)
            joblib.dump(model, model_path)
            
            # Save feature names and model info
            feature_info = {
                "feature_names": list(features_df.columns),
                "date_column": date_col,
                "amount_column": amount_col,
                "category_column": category_col,
                "training_samples": len(X_train),
                "test_samples": len(X_test),
                "train_accuracy": float(train_score),
                "test_accuracy": float(test_score),
                "trained_date": datetime.now().isoformat()
            }
            
            model_info = {
                "model_path": model_path,
                "train_accuracy": float(train_score),
                "test_accuracy": float(test_score),
                "training_samples": len(X_train),
                "test_samples": len(X_test),
                "feature_info": feature_info
            }
            
            # Save to MongoDB if available
            if self.mongodb and self.mongodb.is_connected():
                self.mongodb.save_model_info(user_id, model_info)
            
            # Also save to file system as backup
            from app.tools.csv_tools import normalize_user_id
            safe_id = normalize_user_id(user_id)
            feature_info_path = os.path.join(self.base_dir, f"{safe_id}_features.json")
            with open(feature_info_path, 'w') as f:
                json.dump(feature_info, f, indent=2)
            
            return {
                "success": True,
                "user_id": user_id,
                "model_path": model_path,
                "train_accuracy": float(train_score),
                "test_accuracy": float(test_score),
                "training_samples": len(X_train),
                "retrained": retrain or not os.path.exists(model_path)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_user_model_path(self, user_id: str) -> Optional[str]:
        """
        Get path to user's trained model
        
        Args:
            user_id: Unique user identifier
            
        Returns:
            Path to model file or None if not found
        """
        from app.tools.csv_tools import normalize_user_id
        safe_id = normalize_user_id(user_id)
        model_path = os.path.join(self.base_dir, f"{safe_id}_model.pkl")
        return model_path if os.path.exists(model_path) else None
    
    def get_user_metadata(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user's data metadata
        
        Args:
            user_id: Unique user identifier
            
        Returns:
            Metadata dict or None if not found
        """
        # Try MongoDB first
        if self.mongodb and self.mongodb.is_connected():
            metadata = self.mongodb.get_user_csv_metadata(user_id)
            if metadata:
                return metadata
        
        # Fallback to file system
        from app.tools.csv_tools import normalize_user_id
        safe_id = normalize_user_id(user_id)
        user_dir = os.path.join(self.user_data_dir, safe_id)
        metadata_path = os.path.join(user_dir, "metadata.json")
        
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                return json.load(f)
        return None
    
    def list_users(self) -> List[str]:
        """
        List all users with uploaded data
        
        Returns:
            List of user IDs
        """
        if not os.path.exists(self.user_data_dir):
            return []
        
        users = []
        for item in os.listdir(self.user_data_dir):
            user_path = os.path.join(self.user_data_dir, item)
            if os.path.isdir(user_path) and os.path.exists(os.path.join(user_path, "transactions.csv")):
                users.append(item)
        
        return users

