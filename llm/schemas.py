expense_categorization_schema = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "transaction_id": {"type": ["string", "integer"]},
                    "merchant": {"type": "string"},
                    "amount": {"type": "number"},
                    "predicted_category": {"type": "string"},
                    "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    "reasoning": {"type": "string"}
                },
                "required": ["transaction_id","merchant","amount","predicted_category","confidence","reasoning"],
                "additionalProperties": False
            }
        },
        "summary": {"type": "object", "additionalProperties": {"type": "number"}}
    },
    "required": ["items"],
    "additionalProperties": False
}

budget_monitor_schema = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["Over Budget", "At Risk", "On Track"]},
        "budget_diff": {"type": "number"},
        "utilization": {"type": "number", "minimum": 0.0},
        "report": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "category": {"type": "string"},
                    "spent": {"type": "number"},
                    "limit": {"type": "number"},
                    "utilization": {"type": "number", "minimum": 0.0}
                },
                "required": ["category","spent","limit","utilization"],
                "additionalProperties": False
            }
        },
        "alerts": {"type": "array", "items": {"type": "object"}},
        "recommendations": {"type": "array", "items": {"type": "string"}}
    },
    "required": ["status","budget_diff","utilization","report","recommendations"],
    "additionalProperties": False
}

cashflow_forecast_schema = {
    "type": "object",
    "properties": {
        "forecast": {"type": "array", "items": {"type": "number"}},
        "basis": {"type": "string"},
        "notes": {"type": "array", "items": {"type": "string"}},
        "assumptions": {"type": "object", "additionalProperties": {"type": ["number","string","boolean","object","array"]}}
    },
    "required": ["forecast"],
    "additionalProperties": False
}

query_csv_schema = {
    "type": "object",
    "properties": {
        "rows": {"type": "array", "items": {"type": "object"}},
        "columns": {"type": "array", "items": {"type": "string"}},
        "row_count": {"type": "number"},
        "truncated": {"type": "boolean"},
        "notes": {"type": "string"}
    },
    "required": ["rows","columns","row_count","truncated"],
    "additionalProperties": True
}

spend_aggregate_schema = {
    "type": "object",
    "properties": {
        "month": {"type": "string"},
        "totals": {"type": "array", "items": {"type": "object", "properties": {"key": {"type": "string"}, "spent": {"type": "number"}}, "required": ["key","spent"]}},
        "top": {"type": "array", "items": {"type": "object"}},
        "notes": {"type": "string"}
    },
    "required": ["totals"],
    "additionalProperties": True
}

top_merchants_schema = {
    "type": "object",
    "properties": {
        "month": {"type": "string"},
        "items": {"type": "array", "items": {"type": "object", "properties": {"merchant": {"type": "string"}, "spent": {"type": "number"}, "share": {"type": "number"}}, "required": ["merchant","spent"]}},
        "notes": {"type": "string"}
    },
    "required": ["items"],
    "additionalProperties": True
}

describe_csv_schema = {
    "type": "object",
    "properties": {
        "path": {"type": "string"},
        "columns": {"type": "array", "items": {"type": "object", "properties": {"name": {"type": "string"}, "dtype": {"type": "string"}, "non_null": {"type": "number"}}, "required": ["name"]}},
        "row_estimate": {"type": "number"},
        "sample": {"type": "array", "items": {"type": "object"}}
    },
    "required": ["columns"],
    "additionalProperties": True
}