"""
Parsing Agent: Analyzes user queries and extracts intent
"""
from typing import Dict, Any, List
from llm.llm_client import LLMClient


class ParsingAgent:
    """
    Parses user queries to extract:
    - Query type (transaction analysis, investment advice, market question, etc.)
    - Required data sources
    - Intent and context
    """
    
    def __init__(self, llm_client: LLMClient = None):
        self.llm_client = llm_client or LLMClient()
    
    def parse_query(self, user_query: str, context: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Parse user query to extract intent and requirements
        """
        # Fast path for simple greetings to save quota
        query_lower = user_query.lower().strip()
        greetings = ["hello", "hi", "hey", "good morning", "good evening", "how are you"]
        if query_lower in greetings or len(query_lower) < 4:
            return {
                "query_type": "general_knowledge",
                "intent": "greeting",
                "requires_knowledge": False,
                "requires_transaction_data": False,
                "requires_market_data": False,
                "keywords": [],
                "risk_profile_needed": False
            }

        context_str = ""
        if context:
            recent = context[-3:]  # Last 3 messages
            context_str = "\n".join([f"{msg.get('role', 'user')}: {msg.get('content', '')}" for msg in recent])
        
        # Build context section separately to avoid backslash in f-string expression
        context_section = ""
        if context_str:
            newline = "\n"  # Extract newline to variable to avoid backslash in f-string
            context_section = f"Recent Context:{newline}{context_str}{newline}{newline}"
        
        prompt = f"""Analyze this financial query and extract structured information.

User Query: {user_query}

{context_section}Determine:
1. Query type (transaction_analysis, investment_advice, market_question, general_knowledge, portfolio_question, risk_assessment)
2. Whether it requires knowledge retrieval (VectorDB) - for strategy, market insights, education
3. Whether it requires transaction data (CSV/DB) - for spending, budget, cashflow
4. Whether it requires real-time market data - for current prices, NAV, market conditions
5. Key keywords for knowledge search (if applicable)
6. Whether user risk profile is needed

Respond in JSON format:
{{
    "query_type": "string",
    "intent": "brief description",
    "requires_knowledge": true/false,
    "requires_transaction_data": true/false,
    "requires_market_data": true/false,
    "keywords": ["keyword1", "keyword2"],
    "risk_profile_needed": true/false
}}"""
        
        try:
            response = self.llm_client.complete(prompt)
            
            # Try to extract JSON from response
            import json
            import re
            
            # Find JSON in response
            json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
            else:
                # Fallback: create basic structure
                parsed = self._fallback_parse(user_query)
            
            return parsed
            
        except Exception as e:
            # Fallback parsing
            return self._fallback_parse(user_query)
    
    def _fallback_parse(self, query: str) -> Dict[str, Any]:
        """Fallback parsing using keyword matching + qualitative allocation inference"""
        query_lower = query.lower()
        
        # Determine query type
        if any(word in query_lower for word in ['spend', 'expense', 'budget', 'transaction', 'cashflow']):
            query_type = "transaction_analysis"
            requires_transaction_data = True
            requires_knowledge = False
        elif any(word in query_lower for word in ['invest', 'portfolio', 'sip', 'mutual fund', 'stock', 'allocation']):
            query_type = "investment_advice"
            requires_knowledge = True
            requires_transaction_data = False
        elif any(word in query_lower for word in ['market', 'price', 'nav', 'current']):
            query_type = "market_question"
            requires_market_data = True
            requires_knowledge = True
        else:
            query_type = "general_knowledge"
            requires_knowledge = True
            requires_transaction_data = False
        
        # Extract keywords
        keywords = [word for word in query_lower.split() if len(word) > 3]

        # Heuristic: infer qualitative allocations when user doesn't provide numbers
        inferred_allocation = None
        if query_type == "investment_advice":
            # Buckets we recognize
            buckets = {
                "blue chip": "Large Cap / Blue Chip",
                "large cap": "Large Cap / Blue Chip",
                "index": "Index Funds (Nifty/Sensex)",
                "nifty": "Index Funds (Nifty/Sensex)",
                "sensex": "Index Funds (Nifty/Sensex)",
                "mid cap": "Mid Cap",
                "small cap": "Small Cap",
                "new": "Emerging/Theme Tech",
                "tech": "Emerging/Theme Tech",
                "technology": "Emerging/Theme Tech",
                "sector": "Sector/Thematic",
                "thematic": "Sector/Thematic",
                "gold": "Gold",
                "debt": "Debt",
                "fd": "Fixed Income / FD",
            }

            def present(*phrases):
                return any(p in query_lower for p in phrases)

            # Qualitative intent terms → approximate weights
            # "largely/mostly/primarily" ~ 70-80%
            # "some/minor/a bit" ~ 10-20%
            major_weight = 75
            minor_weight = 15

            major_bucket = None
            minor_bucket = None

            if present("blue chip") or present("large cap"):
                major_bucket = "Large Cap / Blue Chip"
            if present("index") or present("nifty") or present("sensex"):
                # If they mention index and blue chip, index becomes major if major not set
                major_bucket = major_bucket or "Index Funds (Nifty/Sensex)"

            # Minor intents: "some", "minor", "a bit", "small share"
            if present("mid cap"):
                minor_bucket = "Mid Cap"
            elif present("small cap"):
                minor_bucket = "Small Cap"
            elif present("tech") or present("technology") or present("new "):
                minor_bucket = "Emerging/Theme Tech"

            # If user only says "invest largely in blue chip", fill rest with index as minor
            if major_bucket and not minor_bucket:
                minor_bucket = "Index Funds (Nifty/Sensex)"

            if major_bucket or minor_bucket:
                inferred_allocation = []
                if major_bucket:
                    inferred_allocation.append({"bucket": major_bucket, "percent": major_weight})
                if minor_bucket:
                    # Ensure we do not exceed 100
                    remaining = 100 - (inferred_allocation[0]["percent"] if inferred_allocation else 0)
                    inferred_allocation.append({"bucket": minor_bucket, "percent": min(minor_weight, remaining)})

        result = {
            "query_type": query_type,
            "intent": query[:100],
            "requires_knowledge": requires_knowledge,
            "requires_transaction_data": requires_transaction_data,
            "requires_market_data": query_type == "market_question",
            "keywords": keywords[:5],
            "risk_profile_needed": "risk" in query_lower or "investment" in query_lower
        }
        if inferred_allocation:
            result["inferred_allocation"] = inferred_allocation
        return result
        

