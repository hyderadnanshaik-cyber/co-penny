from typing import Any, Tuple, Optional
from jsonschema import validate, Draft202012Validator
from jsonschema.exceptions import ValidationError
import json, re

def validate_json(payload: Any, schema: dict) -> Tuple[bool, Any, Optional[str]]:
    try:
        validate(instance=payload, schema=schema, cls=Draft202012Validator)
        return True, payload, None
    except ValidationError as e:
        return False, payload, str(e)

def _strip_code_fences(s: str) -> str:
    if not s: return s
    s = s.strip()
    if s.startswith("```"): s = re.sub(r"^```[a-zA-Z0-9]*\n", "", s).strip()
    if s.endswith("```"): s = s[:-3].strip()
    return s

def parse_expense_json(txt: str) -> dict:
    """
    Accepts a model response and returns a dict:
    {predicted_category: str, confidence: float, reasoning: str}
    Falls back to 'Other' with low confidence if parsing fails.
    """
    try:
        s = _strip_code_fences(txt)
        obj = json.loads(s)
        cat = obj.get("predicted_category") or obj.get("category") or "Other"
        conf = float(obj.get("confidence", 0.35))
        rsn = obj.get("reasoning") or ""
        return {"predicted_category": str(cat), "confidence": float(conf), "reasoning": str(rsn)}
    except Exception:
        # naive fallback: try to pull category: X from text
        m = re.search(r'(?i)category["\s:]*([A-Za-z ]+)', txt or "")
        cat = (m.group(1).strip() if m else "Other")
        return {"predicted_category": cat, "confidence": 0.2, "reasoning": "fallback parse"}

def parse_budget_json(txt: str) -> dict:
    """
    Accepts a model response and returns a dict compatible with budget monitoring needs:
    {status: str, budget_diff: float, utilization: float, recommendations: [str]}
    Falls back to a conservative default if parsing fails.
    """
    try:
        s = _strip_code_fences(txt)
        obj = json.loads(s)
        status = obj.get("status") or "On Track"
        budget_diff = float(obj.get("budget_diff", 0.0))
        utilization = float(obj.get("utilization", 0.0))
        recs = obj.get("recommendations") or []
        if not isinstance(recs, list):
            recs = [str(recs)]
        return {
            "status": str(status),
            "budget_diff": budget_diff,
            "utilization": utilization,
            "recommendations": [str(r) for r in recs],
        }
    except Exception:
        return {
            "status": "On Track",
            "budget_diff": 0.0,
            "utilization": 0.0,
            "recommendations": ["Enable alerts at 90% of category limits"],
        }

def validate_json_response(txt: str) -> dict:
    """
    General JSON validation function that tries to parse any JSON response
    and returns the parsed object or raises an exception
    """
    try:
        s = _strip_code_fences(txt)
        return json.loads(s)
    except Exception as e:
        raise ValueError(f"Failed to parse JSON response: {e}")