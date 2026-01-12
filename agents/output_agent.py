"""
Output Agent: Formats final response for user
"""
from typing import Dict, Any, List


class OutputAgent:
    """
    Formats the final response combining:
    - Strategy recommendations
    - Risk assessment
    - Transaction insights (if applicable)
    - Knowledge context
    """
    
    def format_response(
        self,
        user_query: str,
        strategy: Dict[str, Any],
        risk_assessment: Dict[str, Any],
        transaction_insights: Dict[str, Any] = None,
        knowledge_sources: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Format final user-friendly response
        
        Returns:
            Dict with formatted answer and metadata
        """
        # Build main answer
        answer_parts = []
        
        # Strategy summary
        if strategy.get('strategy_summary'):
            answer_parts.append(f"**Investment Strategy:**\n{strategy.get('strategy_summary')}")
        
        # Recommendations
        recommendations = risk_assessment.get('adjusted_recommendations') or strategy.get('recommendations', [])
        if recommendations:
            answer_parts.append("\n**Recommended Allocation:**")
            for rec in recommendations[:5]:  # Top 5
                allocation = rec.get('adjusted_allocation') or rec.get('allocation_percentage', 0)
                category = rec.get('category', 'Unknown')
                rationale = rec.get('rationale', '')
                answer_parts.append(f"- **{category}**: {allocation}% - {rationale}")
        
        # Risk notes
        if risk_assessment.get('risk_warnings'):
            answer_parts.append("\n**Risk Considerations:**")
            for warning in risk_assessment.get('risk_warnings', [])[:3]:
                answer_parts.append(f"- {warning}")
        
        # Transaction insights (if available)
        if transaction_insights:
            answer_parts.append("\n**Your Financial Patterns:**")
            if transaction_insights.get('monthly_spend'):
                answer_parts.append(f"- Monthly spending: ₹{transaction_insights.get('monthly_spend', 0):,.0f}")
            if transaction_insights.get('savings_rate'):
                answer_parts.append(f"- Savings rate: {transaction_insights.get('savings_rate', 0):.1f}%")
        
        # Action items
        if strategy.get('action_items'):
            answer_parts.append("\n**Next Steps:**")
            for item in strategy.get('action_items', [])[:5]:
                answer_parts.append(f"- {item}")
        
        # Knowledge sources (for transparency)
        if knowledge_sources:
            sources = set()
            for chunk in knowledge_sources[:3]:
                title = chunk.get('metadata', {}).get('title', 'Unknown')
                if title:
                    sources.add(title)
            if sources:
                answer_parts.append(f"\n*Based on insights from: {', '.join(list(sources))}*")
        
        # Combine into final answer
        final_answer = "\n".join(answer_parts)
        
        return {
            "answer": final_answer,
            "status": "success",
            "type": "strategy_recommendation",
            "metadata": {
                "risk_score": risk_assessment.get('risk_score', 5),
                "risk_alignment": risk_assessment.get('risk_alignment', 'medium'),
                "suitability": risk_assessment.get('suitability', 'suitable'),
                "knowledge_sources_count": len(knowledge_sources) if knowledge_sources else 0
            },
            "data": {
                "strategy": strategy,
                "risk_assessment": risk_assessment
            }
        }
    
    def format_simple_response(
        self,
        answer: str,
        knowledge_sources: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Format a simple text response (for non-strategy queries)"""
        response = {
            "answer": answer,
            "status": "success",
            "type": "text"
        }
        
        if knowledge_sources:
            sources = [chunk.get('metadata', {}).get('title', 'Unknown') for chunk in knowledge_sources[:3]]
            response["metadata"] = {
                "knowledge_sources": sources
            }
        
        return response

