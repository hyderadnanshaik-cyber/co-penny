"""
Risk Agent: Assesses and validates risk alignment
"""
from typing import Dict, Any, Optional, List
from llm.llm_client import LLMClient


class RiskAgent:
    """
    Validates that recommendations align with user risk profile
    and provides risk-adjusted guidance
    """
    
    def __init__(self, llm_client: LLMClient = None):
        self.llm_client = llm_client or LLMClient()
    
    def assess_risk(
        self,
        strategy: Dict[str, Any],
        risk_profile: Dict[str, Any],
        knowledge_context: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Assess risk alignment and provide risk-adjusted recommendations
        
        Args:
            strategy: Strategy recommendations from StrategyAgent
            risk_profile: User risk profile
            knowledge_context: Risk-related knowledge from VectorDB
            
        Returns:
            Dict with risk assessment and adjusted recommendations
        """
        # Extract risk-related knowledge
        risk_knowledge = ""
        if knowledge_context:
            risk_knowledge = "RISK GUIDANCE:\n"
            for chunk in knowledge_context:
                if chunk.get('metadata', {}).get('type') == 'risk_guidance':
                    risk_knowledge += f"- {chunk.get('content', '')}\n"
        
        user_risk = risk_profile.get('risk_tolerance', 'moderate')
        user_goals = risk_profile.get('goals', [])
        
        prompt = f"""You are a risk assessment specialist. Validate and adjust investment strategy based on risk profile.

USER RISK PROFILE:
- Risk tolerance: {user_risk}
- Goals: {user_goals}
- Time horizon: {risk_profile.get('time_horizon', 'medium')}

PROPOSED STRATEGY:
{strategy.get('strategy_summary', 'N/A')}
Recommendations: {strategy.get('recommendations', [])}

{risk_knowledge}

Assess and provide risk-adjusted feedback in JSON:
{{
    "risk_alignment": "high/medium/low (how well strategy matches risk profile)",
    "risk_score": number (1-10, where 10 is highest risk),
    "adjustments_needed": true/false,
    "adjusted_recommendations": [
        {{
            "category": "string",
            "original_allocation": number,
            "adjusted_allocation": number,
            "reason": "why adjustment needed"
        }}
    ],
    "risk_warnings": ["warning1", "warning2"],
    "suitability": "suitable/moderately_suitable/not_suitable"
}}"""
        
        try:
            response = self.llm_client.complete(prompt)
            
            import json
            import re
            json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if json_match:
                assessment = json.loads(json_match.group())
            else:
                assessment = {
                    "risk_alignment": "medium",
                    "risk_score": 5,
                    "adjustments_needed": False,
                    "adjusted_recommendations": [],
                    "risk_warnings": [],
                    "suitability": "suitable"
                }
            
            return assessment
            
        except Exception as e:
            return {
                "risk_alignment": "unknown",
                "risk_score": 5,
                "adjustments_needed": False,
                "adjusted_recommendations": [],
                "risk_warnings": [f"Risk assessment error: {str(e)}"],
                "suitability": "unknown"
            }
    
    def get_risk_profile(self, user_id: str = None) -> Dict[str, Any]:
        """
        Get user risk profile (from MongoDB or file-based storage)
        
        Args:
            user_id: Optional user ID to fetch specific user's profile
        
        Returns:
            Risk profile dictionary
        """
        # Try MongoDB first if user_id is provided
        if user_id:
            try:
                from database.mongodb_service import get_mongodb_service
                mongodb = get_mongodb_service()
                if mongodb.is_connected():
                    profile = mongodb.get_user_profile(user_id)
                    if profile:
                        return {
                            "risk_tolerance": profile.get('risk_preference', 'moderate'),
                            "goals": profile.get('goals', []),
                            "time_horizon": profile.get('time_horizon', 'medium'),
                            "user_id": user_id
                        }
            except Exception:
                pass
        
        # Fallback to file-based profile
        import os
        import json
        try:
            profile_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                'state', 'profile.json'
            )
            if os.path.exists(profile_path):
                with open(profile_path, 'r') as f:
                    profile = json.load(f)
                    return {
                        "risk_tolerance": profile.get('risk_preference', 'moderate'),
                        "goals": profile.get('goals', []),
                        "time_horizon": profile.get('time_horizon', 'medium')
                    }
        except Exception:
            pass
        
        # Default risk profile
        return {
            "risk_tolerance": "moderate",
            "goals": ["wealth_creation", "retirement"],
            "time_horizon": "medium"
        }

