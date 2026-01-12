import os
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

try:
    import duckdb  # type: ignore
    _HAS_DUCKDB = True
except Exception:
    _HAS_DUCKDB = False


# Resolve CSV path relative to the repo root (apex-wealth-agents), not the process CWD
_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_ENV_PATH = os.getenv("CSV_TRANSACTIONS_PATH")
if _ENV_PATH:
    DATA_PATH = _ENV_PATH if os.path.isabs(_ENV_PATH) else os.path.join(_BASE_DIR, _ENV_PATH.replace("/", os.sep))
else:
    DATA_PATH = os.path.join(_BASE_DIR, "data", "transactions.csv")


def get_user_csv_path(user_id: Optional[str] = None, base_path: str = DATA_PATH) -> Optional[str]:
    """Resolve user-specific CSV path if user_id is provided and file exists"""
    if user_id:
        from app.tools.csv_tools import normalize_user_id
        safe_id = normalize_user_id(user_id)
        # Check in state/models/user_data/{safe_id}/transactions.csv
        user_path = os.path.join(_BASE_DIR, "state", "models", "user_data", safe_id, "transactions.csv")
        if os.path.exists(user_path):
            return user_path
    if os.path.exists(base_path):
        return base_path
    return None


def _ensure_csv_exists(path: str) -> None:
    if not os.path.exists(path):
        raise FileNotFoundError(f"CSV not found at {path}")


def _detect_columns(df: pd.DataFrame) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Return best-guess (date_col, amount_col, category_col)."""
    date_col = next((c for c in ["ts", "date", "Date", "DATE"] if c in df.columns), None)
    amount_col = next((c for c in ["amount", "Amount", "AMOUNT", "monthly_expense_total"] if c in df.columns), None)
    category_col = next((c for c in ["category", "Category", "CATEGORY"] if c in df.columns), None)
    return date_col, amount_col, category_col


def _merchant_column(df: pd.DataFrame) -> Optional[str]:
    return next((c for c in ["merchant", "description", "narration", "Merchant", "Description"] if c in df.columns), None)


def _run_duckdb(sql: str, csv_path: str = DATA_PATH) -> pd.DataFrame:
    allowed_starts = ("select", "with")
    first_word = sql.strip().lower().split()[0]
    if first_word not in allowed_starts:
        raise ValueError(f"Only SELECT and WITH queries are allowed. Found: {first_word}")
    con = duckdb.connect(database=":memory:")
    try:
        con.execute(f"CREATE TABLE t AS SELECT * FROM read_csv_auto('{csv_path}', SAMPLE_SIZE=20000)")
        return con.execute(sql).df()
    finally:
        try:
            con.close()
        except Exception:
            pass


def _ym_filter_clause(year: Optional[int], month: Optional[int], date_expr: str = "d") -> str:
    clauses: List[str] = []
    if year is not None:
        clauses.append(f"YEAR({date_expr}) = {int(year)}")
    if month is not None:
        clauses.append(f"MONTH({date_expr}) = {int(month)}")
    return (" AND ".join(clauses)) or "TRUE"


def _normalize_date_sql(date_col: str) -> str:
    """DuckDB-safe conversion of a raw string column to DATE, with fallback parsing."""
    # TRY_CAST handles already-date-like strings; strptime is robust for dd/mm/yy variants
    return (
        f"COALESCE(TRY_CAST({date_col} AS DATE), "
        f"TRY_STRPTIME(CAST({date_col} AS VARCHAR), '%Y-%m-%d'), "
        f"TRY_STRPTIME(CAST({date_col} AS VARCHAR), '%d-%m-%Y'), "
        f"TRY_STRPTIME(CAST({date_col} AS VARCHAR), '%d/%m/%Y'), "
        f"TRY_STRPTIME(CAST({date_col} AS VARCHAR), '%m/%d/%Y'), "
        f"TRY_STRPTIME(CAST({date_col} AS VARCHAR), '%d.%m.%Y')"  # extra common format
        ")"
    )


def _pandas_date_series(df: pd.DataFrame, date_col: str) -> pd.Series:
    return pd.to_datetime(df[date_col], errors="coerce")


def total_spend(year: Optional[int] = None, month: Optional[int] = None, csv_path: Optional[str] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
    """Return total amount spent for optional year and/or month filters."""
    path = csv_path or get_user_csv_path(user_id)
    if not path:
        return {"total": 0.0, "notes": "No data available"}
    _ensure_csv_exists(path)
    if _HAS_DUCKDB:
        df_head = pd.read_csv(path, nrows=1000)
        date_col, amount_col, _ = _detect_columns(df_head)
        if not amount_col:
            return {"total": 0.0, "notes": "amount column not found"}
        d_expr = _normalize_date_sql(date_col) if date_col else "NULL"
        where = _ym_filter_clause(year, month, date_expr="d") if date_col else "TRUE"
        sql = f"""
            WITH s AS (
                SELECT {d_expr} AS d, CAST({amount_col} AS DOUBLE) AS amt FROM t
            )
            SELECT COALESCE(SUM(amt), 0) AS total FROM s WHERE {where}
        """
        df = _run_duckdb(sql, path)
        return {"year": year, "month": month, "total": round(float(df.iloc[0]["total"] or 0.0), 2)}

    df = pd.read_csv(path)
    date_col, amount_col, _ = _detect_columns(df)
    if not amount_col:
        return {"total": 0.0, "notes": "amount column not found"}
    if date_col:
        ds = _pandas_date_series(df, date_col)
        if year is not None:
            df = df[ds.dt.year == int(year)]
        if month is not None:
            df = df[ds.dt.month == int(month)]
    total_val = float(pd.to_numeric(df[amount_col], errors="coerce").sum() or 0.0)
    return {"year": year, "month": month, "total": round(total_val, 2)}


def monthly_spend(year: Optional[int] = None, csv_path: Optional[str] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
    """Return spend aggregated by month. If year provided, filter to that year."""
    path = csv_path or get_user_csv_path(user_id)
    if not path:
        return {"items": [], "notes": "No data available"}
    _ensure_csv_exists(path)
    if _HAS_DUCKDB:
        df_head = pd.read_csv(path, nrows=1000)
        date_col, amount_col, _ = _detect_columns(df_head)
        if not (date_col and amount_col):
            return {"items": [], "notes": "date/amount columns not found"}
        d_expr = _normalize_date_sql(date_col)
        where = _ym_filter_clause(year, None, date_expr="d") if year is not None else "TRUE"
        sql = f"""
            WITH s AS (
                SELECT DATE_TRUNC('month', {d_expr}) AS m, CAST({amount_col} AS DOUBLE) AS amt FROM t
            )
            SELECT CAST(m AS DATE) AS month, SUM(amt) AS spent
            FROM s
            WHERE {where}
            GROUP BY 1
            ORDER BY 1
        """
        df = _run_duckdb(sql, path)
        items = [{"month": str(r["month"]), "spent": round(float(r["spent"] or 0.0), 2)} for _, r in df.iterrows()]
        return {"year": year, "items": items}

    df = pd.read_csv(path)
    date_col, amount_col, _ = _detect_columns(df)
    if not (date_col and amount_col):
        return {"items": [], "notes": "date/amount columns not found"}
    ds = _pandas_date_series(df, date_col)
    if year is not None:
        df = df[ds.dt.year == int(year)]
        ds = _pandas_date_series(df, date_col)
    grp = (
        df.assign(__month=ds.dt.to_period("M").astype(str))
          .groupby("__month")[amount_col]
          .sum()
          .reset_index()
          .sort_values("__month")
    )
    items = [{"month": r["__month"], "spent": round(float(r[amount_col] or 0.0), 2)} for _, r in grp.iterrows()]
    return {"year": year, "items": items}


def daily_spend(year: Optional[int] = None, month: Optional[int] = None, csv_path: Optional[str] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
    """Return spend aggregated by day with optional year/month filters."""
    path = csv_path or get_user_csv_path(user_id)
    if not path:
        return {"items": [], "notes": "No data available"}
    _ensure_csv_exists(path)
    if _HAS_DUCKDB:
        df_head = pd.read_csv(path, nrows=1000)
        date_col, amount_col, _ = _detect_columns(df_head)
        if not (date_col and amount_col):
            return {"items": [], "notes": "date/amount columns not found"}
        d_expr = _normalize_date_sql(date_col)
        where = _ym_filter_clause(year, month, date_expr="d")
        sql = f"""
            WITH s AS (
                SELECT {d_expr} AS d, CAST({amount_col} AS DOUBLE) AS amt FROM t
            )
            SELECT CAST(d AS DATE) AS day, SUM(amt) AS spent
            FROM s
            WHERE {where}
            GROUP BY 1
            ORDER BY 1
        """
        df = _run_duckdb(sql, path)
        items = [{"day": str(r["day"]), "spent": round(float(r["spent"] or 0.0), 2)} for _, r in df.iterrows()]
        return {"year": year, "month": month, "items": items}

    df = pd.read_csv(path)
    date_col, amount_col, _ = _detect_columns(df)
    if not (date_col and amount_col):
        return {"items": [], "notes": "date/amount columns not found"}
    ds = _pandas_date_series(df, date_col)
    if year is not None:
        df = df[ds.dt.year == int(year)]
        ds = _pandas_date_series(df, date_col)
    if month is not None:
        df = df[ds.dt.month == int(month)]
        ds = _pandas_date_series(df, date_col)
    grp = (
        df.assign(__day=ds.dt.date.astype(str))
          .groupby("__day")[amount_col]
          .sum()
          .reset_index()
          .sort_values("__day")
    )
    items = [{"day": r["__day"], "spent": round(float(r[amount_col] or 0.0), 2)} for _, r in grp.iterrows()]
    return {"year": year, "month": month, "items": items}


def category_stats(year: Optional[int] = None, month: Optional[int] = None, csv_path: Optional[str] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
    """Return sum by category with optional year/month filters."""
    path = csv_path or get_user_csv_path(user_id)
    if not path:
        return {"items": [], "notes": "No data available"}
    _ensure_csv_exists(path)
    if _HAS_DUCKDB:
        df_head = pd.read_csv(path, nrows=1000)
        date_col, amount_col, category_col = _detect_columns(df_head)
        if not (amount_col and category_col):
            return {"items": [], "notes": "amount/category columns not found"}
        d_expr = _normalize_date_sql(date_col) if date_col else "NULL"
        where = _ym_filter_clause(year, month, date_expr="d") if date_col else "TRUE"
        sql = f"""
            WITH s AS (
                SELECT {d_expr} AS d, CAST({amount_col} AS DOUBLE) AS amt, {category_col} AS category FROM t
            )
            SELECT category, SUM(amt) AS spent
            FROM s
            WHERE {where}
            GROUP BY 1
            ORDER BY spent DESC
        """
        df = _run_duckdb(sql, path)
        items = [{"category": str(r["category"]), "spent": round(float(r["spent"] or 0.0), 2)} for _, r in df.iterrows()]
        return {"year": year, "month": month, "items": items}

    df = pd.read_csv(path)
    date_col, amount_col, category_col = _detect_columns(df)
    if not (amount_col and category_col):
        return {"items": [], "notes": "amount/category columns not found"}
    if date_col:
        ds = _pandas_date_series(df, date_col)
        if year is not None:
            df = df[ds.dt.year == int(year)]
            ds = _pandas_date_series(df, date_col)
        if month is not None:
            df = df[ds.dt.month == int(month)]
    grp = df.groupby(category_col)[amount_col].sum().reset_index().sort_values(amount_col, ascending=False)
    items = [{"category": str(r[category_col]), "spent": round(float(r[amount_col] or 0.0), 2)} for _, r in grp.iterrows()]
    return {"year": year, "month": month, "items": items}


def merchant_stats(year: Optional[int] = None, month: Optional[int] = None, top_n: int = 10, csv_path: Optional[str] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
    """Return top merchants by spend with optional filters."""
    path = csv_path or get_user_csv_path(user_id)
    if not path:
        return {"items": [], "notes": "No data available"}
    _ensure_csv_exists(path)
    if _HAS_DUCKDB:
        df_head = pd.read_csv(path, nrows=1000)
        date_col, amount_col, _ = _detect_columns(df_head)
        merchant_col = _merchant_column(df_head)
        if not (merchant_col and amount_col):
            return {"items": [], "notes": "merchant/amount columns not found"}
        d_expr = _normalize_date_sql(date_col) if date_col else "NULL"
        where = _ym_filter_clause(year, month, date_expr="d") if date_col else "TRUE"
        sql = f"""
            WITH s AS (
                SELECT {d_expr} AS d, CAST({amount_col} AS DOUBLE) AS amt, {merchant_col} AS merchant FROM t
            )
            SELECT merchant, SUM(amt) AS spent
            FROM s
            WHERE {where}
            GROUP BY 1
            ORDER BY spent DESC
            LIMIT {int(top_n or 10)}
        """
        df = _run_duckdb(sql, path)
        items = [{"merchant": str(r["merchant"]), "spent": round(float(r["spent"] or 0.0), 2)} for _, r in df.iterrows()]
        return {"year": year, "month": month, "items": items}

    df = pd.read_csv(path)
    date_col, amount_col, _ = _detect_columns(df)
    merchant_col = _merchant_column(df)
    if not (merchant_col and amount_col):
        return {"items": [], "notes": "merchant/amount columns not found"}
    if date_col:
        ds = _pandas_date_series(df, date_col)
        if year is not None:
            df = df[ds.dt.year == int(year)]
            ds = _pandas_date_series(df, date_col)
        if month is not None:
            df = df[ds.dt.month == int(month)]
    grp = df.groupby(merchant_col)[amount_col].sum().reset_index().sort_values(amount_col, ascending=False).head(int(top_n or 10))
    items = [{"merchant": str(r[merchant_col]), "spent": round(float(r[amount_col] or 0.0), 2)} for _, r in grp.iterrows()]
    return {"year": year, "month": month, "items": items}


def time_coverage(csv_path: Optional[str] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
    """Return min/max dates found in the dataset."""
    path = csv_path or get_user_csv_path(user_id)
    _ensure_csv_exists(path)
    df = pd.read_csv(path, nrows=50000)
    date_col, _, _ = _detect_columns(df)
    if not date_col:
        return {"min": None, "max": None}
    ds = _pandas_date_series(df, date_col)
    if ds.notna().any():
        return {"min": str(ds.min().date()), "max": str(ds.max().date())}
    return {"min": None, "max": None}


__all__ = [
    "total_spend",
    "monthly_spend",
    "daily_spend",
    "category_stats",
    "merchant_stats",
    "time_coverage",
]

import os
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import re

# Resolve CSV path relative to the repo root (apex-wealth-agents)
_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_DATA_PATH = os.path.join(_BASE_DIR, "data", "transactions.csv")

def _ensure_csv_exists(path: str = _DATA_PATH) -> None:
    """Ensure the CSV file exists"""
    if not os.path.exists(path):
        raise FileNotFoundError(f"CSV not found at {path}")

def _load_data(csv_path: Optional[str] = None, user_id: Optional[str] = None) -> pd.DataFrame:
    """Load and preprocess the transaction data"""
    path = csv_path or get_user_csv_path(user_id)
    if not path:
        return pd.DataFrame()
    _ensure_csv_exists(path)
    df = pd.read_csv(path)
    
    # Convert date column to datetime
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
    
    # Ensure amount columns are numeric
    amount_columns = ['monthly_expense_total', 'amount', 'Amount', 'AMOUNT']
    for col in amount_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    return df

def extract_year_data(year: int, csv_path: Optional[str] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
    """Extract all data for a specific year"""
    try:
        df = _load_data(csv_path, user_id)
        
        # Filter by year
        year_data = df[df['date'].dt.year == year].copy()
        
        if year_data.empty:
            return {
                "year": year,
                "total_transactions": 0,
                "total_spent": 0,
                "categories": [],
                "monthly_breakdown": [],
                "top_merchants": [],
                "data_available": False
            }
        
        # Calculate totals
        total_spent = year_data['monthly_expense_total'].sum()
        total_transactions = len(year_data)
        
        # Category breakdown
        category_breakdown = year_data.groupby('category')['monthly_expense_total'].sum().reset_index()
        category_breakdown = category_breakdown.sort_values('monthly_expense_total', ascending=False)
        categories = category_breakdown.to_dict('records')
        
        # Monthly breakdown
        year_data['month'] = year_data['date'].dt.month
        monthly_breakdown = year_data.groupby('month')['monthly_expense_total'].sum().reset_index()
        monthly_breakdown['month_name'] = monthly_breakdown['month'].apply(lambda x: datetime(2000, x, 1).strftime('%B'))
        monthly_data = monthly_breakdown.to_dict('records')
        
        # Top merchants (if merchant column exists)
        top_merchants = []
        if 'merchant' in year_data.columns:
            merchant_breakdown = year_data.groupby('merchant')['monthly_expense_total'].sum().reset_index()
            merchant_breakdown = merchant_breakdown.sort_values('monthly_expense_total', ascending=False).head(10)
            top_merchants = merchant_breakdown.to_dict('records')
        
        return {
            "year": year,
            "total_transactions": total_transactions,
            "total_spent": float(total_spent),
            "categories": categories,
            "monthly_breakdown": monthly_data,
            "top_merchants": top_merchants,
            "data_available": True
        }
        
    except Exception as e:
        return {
            "year": year,
            "error": str(e),
            "data_available": False
        }

def extract_year_range_data(start_year: int, end_year: int, csv_path: Optional[str] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
    """Extract data for a range of years"""
    try:
        df = _load_data(csv_path, user_id)
        
        # Filter by year range
        range_data = df[(df['date'].dt.year >= start_year) & (df['date'].dt.year <= end_year)].copy()
        
        if range_data.empty:
            return {
                "start_year": start_year,
                "end_year": end_year,
                "total_transactions": 0,
                "total_spent": 0,
                "yearly_breakdown": [],
                "categories": [],
                "data_available": False
            }
        
        # Calculate totals
        total_spent = range_data['monthly_expense_total'].sum()
        total_transactions = len(range_data)
        
        # Yearly breakdown
        range_data['year'] = range_data['date'].dt.year
        yearly_breakdown = range_data.groupby('year')['monthly_expense_total'].sum().reset_index()
        yearly_breakdown = yearly_breakdown.sort_values('year')
        yearly_data = yearly_breakdown.to_dict('records')
        
        # Category breakdown
        category_breakdown = range_data.groupby('category')['monthly_expense_total'].sum().reset_index()
        category_breakdown = category_breakdown.sort_values('monthly_expense_total', ascending=False)
        categories = category_breakdown.to_dict('records')
        
        return {
            "start_year": start_year,
            "end_year": end_year,
            "total_transactions": total_transactions,
            "total_spent": float(total_spent),
            "yearly_breakdown": yearly_data,
            "categories": categories,
            "data_available": True
        }
        
    except Exception as e:
        return {
            "start_year": start_year,
            "end_year": end_year,
            "error": str(e),
            "data_available": False
        }

def extract_month_data(year: int, month: int, csv_path: Optional[str] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
    """Extract data for a specific month"""
    try:
        df = _load_data(csv_path, user_id)
        
        # Filter by year and month
        month_data = df[(df['date'].dt.year == year) & (df['date'].dt.month == month)].copy()
        
        if month_data.empty:
            return {
                "year": year,
                "month": month,
                "month_name": datetime(year, month, 1).strftime('%B'),
                "total_transactions": 0,
                "total_spent": 0,
                "categories": [],
                "data_available": False
            }
        
        # Calculate totals
        total_spent = month_data['monthly_expense_total'].sum()
        total_transactions = len(month_data)
        
        # Category breakdown
        category_breakdown = month_data.groupby('category')['monthly_expense_total'].sum().reset_index()
        category_breakdown = category_breakdown.sort_values('monthly_expense_total', ascending=False)
        categories = category_breakdown.to_dict('records')
        
        return {
            "year": year,
            "month": month,
            "month_name": datetime(year, month, 1).strftime('%B'),
            "total_transactions": total_transactions,
            "total_spent": float(total_spent),
            "categories": categories,
            "data_available": True
        }
        
    except Exception as e:
        return {
            "year": year,
            "month": month,
            "month_name": datetime(year, month, 1).strftime('%B'),
            "error": str(e),
            "data_available": False
        }

def extract_date_range_data(start_date: str, end_date: str, csv_path: Optional[str] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
    """Extract data for a specific date range (format: YYYY-MM-DD)"""
    try:
        df = _load_data(csv_path, user_id)
        
        # Convert date strings to datetime
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        
        # Filter by date range
        range_data = df[(df['date'] >= start_dt) & (df['date'] <= end_dt)].copy()
        
        if range_data.empty:
            return {
                "start_date": start_date,
                "end_date": end_date,
                "total_transactions": 0,
                "total_spent": 0,
                "categories": [],
                "data_available": False
            }
        
        # Calculate totals
        total_spent = range_data['monthly_expense_total'].sum()
        total_transactions = len(range_data)
        
        # Category breakdown
        category_breakdown = range_data.groupby('category')['monthly_expense_total'].sum().reset_index()
        category_breakdown = category_breakdown.sort_values('monthly_expense_total', ascending=False)
        categories = category_breakdown.to_dict('records')
        
        return {
            "start_date": start_date,
            "end_date": end_date,
            "total_transactions": total_transactions,
            "total_spent": float(total_spent),
            "categories": categories,
            "data_available": True
        }
        
    except Exception as e:
        return {
            "start_date": start_date,
            "end_date": end_date,
            "error": str(e),
            "data_available": False
        }

def parse_historical_query(query: str) -> Dict[str, Any]:
    """Parse a historical query to extract year, month, or date range information"""
    query_lower = query.lower()
    
    # Extract years mentioned
    years = re.findall(r'\b(20\d{2})\b', query)
    
    # Extract months mentioned
    months = []
    month_names = ['january', 'february', 'march', 'april', 'may', 'june',
                   'july', 'august', 'september', 'october', 'november', 'december']
    for i, month in enumerate(month_names, 1):
        if month in query_lower:
            months.append(i)
    
    # Extract date ranges
    date_patterns = [
        r'(\d{4}-\d{2}-\d{2})\s+to\s+(\d{4}-\d{2}-\d{2})',
        r'from\s+(\d{4}-\d{2}-\d{2})\s+to\s+(\d{4}-\d{2}-\d{2})',
        r'between\s+(\d{4}-\d{2}-\d{2})\s+and\s+(\d{4}-\d{2}-\d{2})'
    ]
    
    date_range = None
    for pattern in date_patterns:
        match = re.search(pattern, query)
        if match:
            date_range = (match.group(1), match.group(2))
            break
    
    return {
        "years": [int(y) for y in years],
        "months": months,
        "date_range": date_range,
        "query_type": "year" if years else "month" if months else "date_range" if date_range else "general"
    }

def get_available_years(csv_path: Optional[str] = None, user_id: Optional[str] = None) -> List[int]:
    """Get list of available years in the dataset"""
    try:
        df = _load_data(csv_path, user_id)
        years = sorted(df['date'].dt.year.dropna().unique().tolist())
        return years
    except Exception as e:
        return []

def format_currency(amount: float) -> str:
    """Format amount as Indian Rupees with commas"""
    return f"₹{amount:,.2f}"

def format_date(date_str: str) -> str:
    """Format date as DD/MM/YYYY"""
    try:
        dt = pd.to_datetime(date_str)
        return dt.strftime('%d/%m/%Y')
    except:
        return date_str
