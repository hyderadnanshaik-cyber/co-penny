import os
import csv
from typing import Any, Dict, List, Optional
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


def normalize_user_id(user_id: str) -> str:
	"""Normalize user ID for filesystem usage (replace dots and spaces with underscores)"""
	if not user_id:
		return "guest"
	return str(user_id).replace(".", "_").replace(" ", "_").strip()


def get_user_csv_path(user_id: Optional[str] = None, base_path: str = DATA_PATH) -> Optional[str]:
	"""Resolve user-specific CSV path if user_id is provided and file exists"""
	if user_id:
		# Normalize ID for filesystem
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


def query_csv(sql: str, limit: int = 1000, csv_path: Optional[str] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
	"""
	Run safe SELECT over the transactions CSV. If duckdb unavailable, return head().
	"""
	path = csv_path or get_user_csv_path(user_id)
	if not path:
		return {"rows": [], "columns": [], "error": "No transaction data available. Please upload a CSV file."}
	_ensure_csv_exists(path)
	limit = int(limit or 1000)
	if limit <= 0 or limit > 10000:
		limit = 1000
	if not isinstance(sql, str) or not sql.strip():
		sql = "SELECT * FROM t LIMIT {limit}".format(limit=limit)

	if _HAS_DUCKDB:
		con = duckdb.connect(database=':memory:')
		try:
			# deny non-SELECT
			if sql.strip().lower().split()[0] != "select":
				raise ValueError("Only SELECT queries are allowed")
			# register CSV as table t
			con.execute(f"CREATE TABLE t AS SELECT * FROM read_csv_auto('{path}', SAMPLE_SIZE=20000)")
			q = sql
			if " limit " not in sql.lower():
				q = sql.rstrip("; ") + f" LIMIT {limit}"
			df = con.execute(q).df()
			rows = df.to_dict(orient='records')
			return {
				"rows": rows,
				"columns": list(df.columns),
				"row_count": len(rows),
				"truncated": len(rows) >= limit,
			}
		finally:
			try:
				con.close()
			except Exception:
				pass

	# Fallback: no duckdb → return first N rows via pandas
	df = pd.read_csv(path)
	rows = df.head(limit).to_dict(orient='records')
	return {
		"rows": rows,
		"columns": list(df.columns),
		"row_count": len(rows),
		"truncated": len(df) > len(rows),
		"notes": "duckdb not installed; returned first rows",
	}


def spend_aggregate(month: Optional[str] = None, group_by: str = "category", csv_path: Optional[str] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
	path = csv_path or get_user_csv_path(user_id)
	if not path:
		return {"totals": [], "notes": "No transaction data available"}
	_ensure_csv_exists(path)
	df = pd.read_csv(path)
	# normalize columns
	date_col = None
	for c in ["ts","date","Date","DATE"]:
		if c in df.columns:
			date_col = c
			break
	if date_col is None:
		df["__month"] = None
	else:
		df["__month"] = pd.to_datetime(df[date_col], errors='coerce').dt.to_period("M").astype(str)
	if month:
		df = df[df["__month"] == month]

	amt_col = None
	for c in ["amount","Amount","AMOUNT","monthly_expense_total"]:
		if c in df.columns:
			amt_col = c
			break
	if amt_col is None:
		return {"totals": [], "notes": "amount column not found"}

	key = group_by if group_by in df.columns else ("category" if "category" in df.columns else None)
	if key is None:
		return {"totals": [], "notes": "group_by column not found"}

	grp = df.groupby(key, dropna=False)[amt_col].sum().reset_index().rename(columns={key: "key", amt_col: "spent"})
	grp["spent"] = grp["spent"].astype(float).round(2)
	totals = grp.sort_values("spent", ascending=False).to_dict(orient='records')
	return {"month": month or "all", "totals": totals, "top": totals[:5]}


def top_merchants(month: Optional[str] = None, n: int = 10, csv_path: Optional[str] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
	path = csv_path or get_user_csv_path(user_id)
	if not path:
		return {"items": [], "notes": "No transaction data available"}
	_ensure_csv_exists(path)
	df = pd.read_csv(path)
	# month filter
	date_col = None
	for c in ["ts","date","Date","DATE"]:
		if c in df.columns:
			date_col = c
			break
	if date_col is not None:
		df["__month"] = pd.to_datetime(df[date_col], errors='coerce').dt.to_period("M").astype(str)
		if month:
			df = df[df["__month"] == month]
	merchant_col = None
	for c in ["merchant","description","narration","Merchant","Description"]:
		if c in df.columns:
			merchant_col = c
			break
	amt_col = None
	for c in ["amount","Amount","AMOUNT","monthly_expense_total"]:
		if c in df.columns:
			amt_col = c
			break
	if merchant_col is None or amt_col is None:
		return {"items": [], "notes": "merchant/amount column missing"}
	grp = df.groupby(merchant_col, dropna=False)[amt_col].sum().reset_index().rename(columns={merchant_col: "merchant", amt_col: "spent"})
	grp["spent"] = grp["spent"].astype(float)
	total_spent = float(grp["spent"].sum() or 0.0) or 1.0
	grp["share"] = (grp["spent"] / total_spent).round(4)
	items = grp.sort_values("spent", ascending=False).head(int(n or 10))
	items["spent"] = items["spent"].round(2)
	return {"month": month or "all", "items": items.to_dict(orient='records')}


def describe_csv(csv_path: Optional[str] = None, sample_rows: int = 20, user_id: Optional[str] = None) -> Dict[str, Any]:
	path = csv_path or get_user_csv_path(user_id)
	if not path:
		return {"columns": [], "row_estimate": 0, "sample": [], "notes": "No data"}
	_ensure_csv_exists(path)
	df = pd.read_csv(path, nrows=max(1000, sample_rows))
	cols = []
	for c in df.columns:
		series = df[c]
		dtype = str(series.dtype)
		non_null = int(series.notna().sum())
		cols.append({"name": c, "dtype": dtype, "non_null": non_null})
	sample = df.head(sample_rows).to_dict(orient='records')
	return {
		"path": path,
		"columns": cols,
		"row_estimate": int(len(df)),
		"sample": sample,
	}


