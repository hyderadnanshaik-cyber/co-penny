"""
Strategy Agent: Generates investment strategies based on knowledge and context
"""
from typing import Dict, Any, List
from llm.llm_client import LLMClient


class StrategyAgent:
    """
    Generates investment strategies by combining:
    - Retrieved knowledge from VectorDB
    - User risk profile
    - Current market context
    - Transaction patterns (if available)
    """
    
    def __init__(self, llm_client: LLMClient = None):
        self.llm_client = llm_client or LLMClient()
    
    def generate_strategy(
        self,
        user_query: str,
        knowledge_context: List[Dict[str, Any]],
        risk_profile: Dict[str, Any] = None,
        transaction_summary: Dict[str, Any] = None,
        market_context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Generate investment strategy recommendation
        
        Args:
            user_query: Original user query
            knowledge_context: Retrieved knowledge chunks from VectorDB
            risk_profile: User risk profile (if available)
            transaction_summary: Summary of transaction patterns (if available)
            market_context: Current market data (if available)
            
        Returns:
            Dict with strategy recommendations
        """
        # Build knowledge context string
        knowledge_text = ""
        if knowledge_context:
            knowledge_text = "RELEVANT KNOWLEDGE:\n"
            for i, chunk in enumerate(knowledge_context[:5], 1):  # Top 5 chunks
                knowledge_text += f"\n[{i}] {chunk.get('content', '')}\n"
                if chunk.get('metadata'):
                    knowledge_text += f"   Source: {chunk.get('metadata', {}).get('title', 'Unknown')}\n"
        
        # Build risk profile context
        risk_text = ""
        if risk_profile:
            risk_text = f"\nUSER RISK PROFILE:\n"
            risk_text += f"- Risk tolerance: {risk_profile.get('risk_tolerance', 'moderate')}\n"
            risk_text += f"- Investment goals: {risk_profile.get('goals', [])}\n"
            risk_text += f"- Time horizon: {risk_profile.get('time_horizon', 'medium')}\n"
        
        # Build transaction context
        transaction_text = ""
        if transaction_summary:
            transaction_text = f"\nTRANSACTION PATTERNS:\n"
            transaction_text += f"- Monthly spending: {transaction_summary.get('monthly_spend', 'N/A')}\n"
            transaction_text += f"- Savings rate: {transaction_summary.get('savings_rate', 'N/A')}\n"
            transaction_text += f"- Top categories: {transaction_summary.get('top_categories', [])}\n"
        
        # Build market context
        market_text = ""
        if market_context:
            market_text = f"\nCURRENT MARKET CONTEXT:\n"
            market_text += f"- Market conditions: {market_context.get('conditions', 'N/A')}\n"
            market_text += f"- Key indicators: {market_context.get('indicators', {})}\n"
        
        prompt = f"""You are a financial strategy advisor. Generate a personalized investment strategy based on the provided context.

USER QUERY: {user_query}

{knowledge_text}

{risk_text}

{transaction_text}

{market_text}

Generate a comprehensive strategy recommendation in JSON format:
{{
    "strategy_summary": "Brief 2-3 sentence summary",
    "recommendations": [
        {{
            "category": "string (e.g., Equity, Debt, Hybrid)",
            "allocation_percentage": number,
            "rationale": "why this allocation",
            "specific_products": ["product1", "product2"] (optional)
        }}
    ],
    "action_items": ["action1", "action2"],
    "risk_notes": "risk considerations",
    "time_horizon": "short/medium/long term focus"
}}

Be specific, data-driven, and align with the user's risk profile and goals."""
        
        try:
            response = self.llm_client.complete(prompt)
            
            # Extract JSON
            import json
            import re
            json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {
                    "strategy_summary": response[:200],
                    "recommendations": [],
                    "action_items": [],
                    "risk_notes": "",
                    "time_horizon": "medium"
                }
        except Exception as e:
            return {
                "strategy_summary": f"Strategy generation encountered an error: {str(e)}",
                "recommendations": [],
                "action_items": [],
                "risk_notes": "",
                "time_horizon": "medium"
            }

