import json
import os
from typing import List, Dict, Any, Optional
from llm.llm_client import LLMClient
from llm.prompts import system_advisor
from llm.json_guard import validate_json_response
from app.tools.csv_tools import query_csv, spend_aggregate, top_merchants, describe_csv
from app.tools.visualization import generate_visualizations, generate_dynamic_visualizations
from app.tools.enhanced_csv_tools import (
    total_spend,
    monthly_spend,
    daily_spend,
    category_stats,
    merchant_stats,
    time_coverage,
)

# VectorDB and Agent imports
try:
    from vectordb.knowledge_store import get_knowledge_store
    from agents.parsing_agent import ParsingAgent
    from agents.strategy_agent import StrategyAgent
    from agents.risk_agent import RiskAgent
    from agents.output_agent import OutputAgent
    from agents.analysis_agent import AnalysisAgent
    from agents.implementation_agent import ImplementationAgent
    VECTORDB_AVAILABLE = True
except ImportError:
    VECTORDB_AVAILABLE = False
    get_knowledge_store = None
    ParsingAgent = None
    StrategyAgent = None
    RiskAgent = None
    OutputAgent = None
    AnalysisAgent = None
    ImplementationAgent = None

class EnhancedOrchestrator:
    def __init__(self):
        self.llm_client = LLMClient()
        
        # Initialize VectorDB components if available
        if VECTORDB_AVAILABLE:
            try:
                self.knowledge_store = get_knowledge_store()
                self.parsing_agent = ParsingAgent(self.llm_client)
                self.strategy_agent = StrategyAgent(self.llm_client)
                self.risk_agent = RiskAgent(self.llm_client)
                self.output_agent = OutputAgent()
                self.analysis_agent = AnalysisAgent() if AnalysisAgent else None
                self.implementation_agent = ImplementationAgent() if ImplementationAgent else None
                self.use_vectordb = False # Streamlined for speed
            except Exception as e:
                print(f"Warning: VectorDB initialization failed: {e}. Continuing without VectorDB.")
                self.use_vectordb = False
                self.analysis_agent = None
        else:
            self.use_vectordb = False
            self.analysis_agent = None
        
    def _extract_year_month(self, message: str) -> tuple:
        """Extract year and optional month integer from free-form text."""
        import re
        msg = message.lower()
        # Year: any 4-digit between 1900-2099
        year = None
        m = re.search(r"\b(19\d{2}|20\d{2})\b", msg)
        if m:
            year = int(m.group(1))
        # Month by number or name
        month = None
        # numeric MM or M
        mnum = re.search(r"\b(1[0-2]|0?[1-9])\s*(?:/|-|\\s|,|\b)\s*(?:'?(?:19\d{2}|20\d{2}))?\b", msg)
        # month names
        months = {
            'january':1,'february':2,'march':3,'april':4,'may':5,'june':6,
            'july':7,'august':8,'september':9,'sept':9,'october':10,'november':11,'december':12,
            'jan':1,'feb':2,'mar':3,'apr':4,'jun':6,'jul':7,'aug':8,'oct':10,'nov':11,'dec':12
        }
        for name, idx in months.items():
            if re.search(rf"\b{name}\b", msg):
                month = idx
                break
        if month is None and mnum:
            try:
                month = int(mnum.group(1))
            except Exception:
                month = None
        return year, month

    def _should_generate_charts(self, message: str) -> bool:
        """Determine if charts should be generated based on the message"""
        chart_keywords = [
            'chart', 'graph', 'plot', 'visualize', 'visualization', 'show me',
            'display', 'picture', 'image', 'diagram', 'breakdown', 'analysis',
            'trend', 'pattern', 'comparison', 'distribution', 'pie', 'bar', 'line',
            'histogram', 'monthly', 'daily', 'weekly', 'timeline', 'over time',
            'amount', 'spending', 'category', 'merchant', 'top', 'highest',
            'compare', 'vs', 'versus', 'create', 'generate', 'make', 'expenditure'
        ]
        return any(keyword in message.lower() for keyword in chart_keywords)

    def _get_comprehensive_data_context(self, message: str, user_id: Optional[str] = None) -> tuple:
        """
        Get comprehensive data context for the LLM based on the user's question
        """
        try:
            # Check if this is a data-related question
            data_keywords = [
                'spending', 'expense', 'budget', 'category', 'monthly', 'historical',
                'trend', 'pattern', 'analysis', 'breakdown', 'summary', 'total',
                'how much', 'what did', 'when did', 'where did', 'merchant', 'chart',
                'graph', 'plot', 'visualize', 'show me', 'data', 'transaction', 'update',
                'dashboard', 'current', 'latest', 'status', 'tell me about', 'show',
                'spending habits', 'my money', 'financial', 'how much'
            ]
            
            if not any(keyword in message.lower() for keyword in data_keywords):
                return "", {}
            
            # Get basic data context (always needed for data questions)
            csv_info = describe_csv(user_id=user_id)
            
            # Get subscription info
            from database.mongodb_service import get_mongodb_service
            db = get_mongodb_service()
            sub = db.get_user_subscription(user_id)
            tier = sub.get("tier", "free")

            # Build context based on question type
            context_parts = []
            context_parts.append(f"USER SUBSCRIPTION TIER: {tier.upper()}")
            
            # Basic data overview
            row_count = csv_info.get('row_estimate', 0)
            print(f"DEBUG: orchestrator _get_comprehensive_data_context: user_id={user_id}, row_count={row_count}, tier={tier}") # Debug print
            
            try:
                rc = int(row_count)
            except:
                rc = 0

            if rc == 0:
                # Double check with a direct path check if row_estimate failed
                from app.tools.csv_tools import get_user_csv_path
                path = get_user_csv_path(user_id=user_id)
                if not path:
                     return "SYSTEM ALERT: NO DATA AVAILABLE. The user has NOT uploaded any transaction data. You MUST NOT provide any analysis, fake numbers, or dates. You MUST reply with exactly: 'I do not have access to your financial data yet. Please upload a CSV file in the Data Management section so I can help you.' Do not say anything else.", {}

            context_parts.append(f"DATA OVERVIEW:")
            context_parts.append(f"- Total records: {row_count}")
            context_parts.append(f"- Date range: {self._get_date_range(user_id=user_id)}")
            
            # Extract year/month intent
            year, month = self._extract_year_month(message)
            
            # Get specific data based on question type
            specific_analysis = self._get_specific_analysis(message, user_id=user_id)
            if specific_analysis:
                context_parts.append(f"\nSPECIFIC ANALYSIS:")
                context_parts.append(specific_analysis)
            
            # Generate visualizations when analysis is requested, or time filters provided
            visualizations = {}
            should_chart = self._should_generate_charts(message)
            if any(w in message.lower() for w in ["analyze", "analysis", "breakdown", "insight", "overview", "show", "plot", "chart", "graph", "visualize", "expenditure", "spending"]):
                should_chart = True
            if (year is not None or month is not None):
                # If user specified a time filter, default to generating charts relevant to spend/category
                should_chart = True
            if should_chart:
                try:
                    # Build filtered inputs for visualizations
                    # recent_data filtered by year/month if provided
                    where = ""
                    if year and month:
                        where = f" WHERE CAST(date AS VARCHAR) LIKE '{year}-{month:02d}%'"
                    elif year:
                        where = f" WHERE CAST(date AS VARCHAR) LIKE '{year}%'"
                    recent_sql = (
                        "SELECT date, amount FROM t" + where + " ORDER BY date ASC LIMIT 5000"
                    )
                    recent_data = query_csv(recent_sql, limit=5000, user_id=user_id)
                    # attach meta label for time range
                    label_parts = []
                    if year:
                        label_parts.append(str(year))
                    if month:
                        label_parts.append(f"{month:02d}")
                    time_label = "-".join(label_parts) if label_parts else "all time"
                    recent_data = {**recent_data, "meta": {"label": time_label}}

                    # category-based spending data mapped to expected shape
                    cat = category_stats(year=year, month=month, user_id=user_id)
                    spending_data = {
                        "totals": [
                            {"key": it.get("category", "Unknown"), "spent": it.get("spent", 0.0)}
                            for it in cat.get("items", [])
                        ],
                        "meta": {"label": time_label}
                    }

                    # top merchants
                    merchants_data = merchant_stats(year=year, month=month, top_n=10, user_id=user_id)
                    merchants_data = {**merchants_data, "meta": {"label": time_label}}

                    # Generate dynamic visualizations based on user request
                    visualizations = generate_dynamic_visualizations(message, spending_data, recent_data, merchants_data)
                except Exception as e:
                    print(f"Visualization error: {e}")
                    visualizations = {}
            
            analysis = "\n".join(context_parts)
            return analysis, visualizations
            
        except Exception as e:
            return f"Error analyzing transaction data: {str(e)}", {}

    def _get_date_range(self, user_id: Optional[str] = None) -> str:
        """Get the date range of the transaction data"""
        try:
            cov = time_coverage(user_id=user_id)
            if cov.get("min") or cov.get("max"):
                return f"{cov.get('min', 'Unknown')} to {cov.get('max', 'Unknown')}"
            return "Unknown"
        except Exception as e:
            print(f"Date range error: {e}")
            return "Unknown"

    def _get_specific_analysis(self, message: str, user_id: Optional[str] = None) -> str:
        """Get specific analysis based on the user's question - optimized for speed"""
        try:
            message_lower = message.lower()
            
            # Use query_csv with user_id
            def q(sql): return query_csv(sql, user_id=user_id)
            if any(word in message_lower for word in ['monthly', 'month', 'this month', 'last month']):
                monthly_data = q("""
                    SELECT 
                        strftime('%Y-%m', date) as month,
                        SUM(amount) as total_spent,
                        COUNT(*) as transaction_count
                    FROM t 
                    GROUP BY strftime('%Y-%m', date) 
                    ORDER BY month DESC 
                    LIMIT 6
                """)
                if monthly_data.get('rows'):
                    analysis = "MONTHLY SPENDING:\n"
                    for row in monthly_data['rows'][:3]:  # Show only top 3 months
                        analysis += f"- {row.get('month', 'N/A')}: ₹{row.get('total_spent', 0):,.0f}\n"
                    return analysis
            
            # Category analysis - simplified
            if any(word in message_lower for word in ['category', 'categories', 'spending by', 'top spending']):
                category_breakdown = q("""
                    SELECT 
                        category,
                        SUM(monthly_expense_total) as total
                    FROM t 
                    WHERE category IS NOT NULL AND category != ''
                    GROUP BY category 
                    ORDER BY total DESC 
                    LIMIT 5
                """)
                if category_breakdown.get('rows'):
                    analysis = "TOP SPENDING CATEGORIES:\n"
                    for row in category_breakdown['rows']:
                        analysis += f"- {row.get('category', 'Unknown')}: ₹{row.get('total', 0):,.0f}\n"
                    return analysis
            
            # Merchant analysis - simplified
            if any(word in message_lower for word in ['merchant', 'merchants', 'where did', 'spent on', 'top merchants']):
                merchant_breakdown = q("""
                    SELECT 
                        merchant,
                        SUM(amount) as total
                    FROM t 
                    WHERE merchant IS NOT NULL AND merchant != ''
                    GROUP BY merchant 
                    ORDER BY total DESC 
                    LIMIT 5
                """)
                if merchant_breakdown.get('rows'):
                    analysis = "TOP MERCHANTS:\n"
                    for row in merchant_breakdown['rows']:
                        analysis += f"- {row.get('merchant', 'Unknown')}: ₹{row.get('total', 0):,.0f}\n"
                    return analysis
            
            # Year/month specific analysis (generic)
            y, m = self._extract_year_month(message)
            if y is not None or m is not None:
                ts = total_spend(year=y, month=m, user_id=user_id)
                parts = [f"FILTER: year={y or 'all'} month={m or 'all'}", f"- Total spent: ₹{ts.get('total', 0.0):,.0f}"]
                cats = category_stats(year=y, month=m, user_id=user_id)
                if cats.get("items"):
                    topcats = ", ".join([f"{it['category']}: ₹{it['spent']:,.0f}" for it in cats['items'][:3]])
                    parts.append(f"- Top categories: {topcats}")
                merch = merchant_stats(year=y, month=m, top_n=3, user_id=user_id)
                if merch.get("items"):
                    topm = ", ".join([f"{it['merchant']}: ₹{it['spent']:,.0f}" for it in merch['items']])
                    parts.append(f"- Top merchants: {topm}")
                return "\n".join(parts)
            
            # Quick summary for general questions
            if any(word in message_lower for word in ['summary', 'overview', 'total', 'how much']):
                summary_data = q("""
                    SELECT 
                        SUM(monthly_expense_total) as total_spent,
                        COUNT(*) as transaction_count,
                        AVG(monthly_expense_total) as avg_transaction
                    FROM t
                """)
                if summary_data.get('rows'):
                    row = summary_data['rows'][0]
                    analysis = f"QUICK SUMMARY:\n- Total spent: ₹{row.get('total_spent', 0):,.0f}\n- Transactions: {row.get('transaction_count', 0)}\n- Avg per transaction: ₹{row.get('avg_transaction', 0):,.0f}\n"
                    return analysis
            
            return ""
            
        except Exception as e:
            return f"Error in specific analysis: {str(e)}"

    def craft_advisor_reply(self, user_message: str, observations_text: str = "") -> str:
        """
        Craft a concise advisor reply with data context (integrated from advisor_reply.py)
        """
        guidance = (
            "Write a concise advisor reply. Start with a one-line assessment. "
            "Then provide up to four bullet points of actions or numbers. "
            "If you need a file or confirmation, ask one short question at the end."
        )
        
        # Lightweight CSV context so the model knows the available columns immediately
        try:
            meta = describe_csv(user_id=None) # Use base CSV for columns info if needed
            colnames = ", ".join([c.get("name","?") for c in meta.get("columns", [])][:12])
            sample_rows = meta.get("sample", [])[:2]
            data_context = f"Data columns: {colnames}. Sample rows: {sample_rows}"
        except Exception:
            data_context = "Data columns: (unavailable)"
        
        prompt = f"{system_advisor}\nData Context:\n{data_context}\nObservations:\n{observations_text}\nUser: {user_message}\n{guidance}\nFinal answer:"
        return self.llm_client.complete(prompt).strip()

    def _process_with_vectordb_workflow(
        self,
        message: str,
        context: List[Dict[str, str]] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process query using VectorDB workflow:
        User Query → Parsing Agent → Embedding → VectorDB Search → Strategy Agent → Risk Agent → Output Agent
        """
        try:
            # Step 1: Parsing Agent - Extract intent and requirements
            parsed = self.parsing_agent.parse_query(message, context)
            
            # Step 2: Retrieve knowledge from VectorDB if needed
            knowledge_context = []
            if parsed.get('requires_knowledge', False):
                query_keywords = ' '.join(parsed.get('keywords', [message]))
                knowledge_context = self.knowledge_store.retrieve_knowledge(
                    query=query_keywords,
                    namespace=None,  # Search all namespaces
                    top_k=5
                )
            
            # Step 3: Get transaction data if needed
            transaction_summary = None
            financial_analysis = None
            if parsed.get('requires_transaction_data', False):
                try:
                    # Get basic transaction summary
                    total = total_spend(user_id=user_id)
                    monthly = monthly_spend(user_id=user_id)
                    categories = category_stats(user_id=user_id)
                    
                    # Get category breakdown for expenses
                    category_breakdown = {}
                    if categories.get('items'):
                        for item in categories.get('items', []):
                            cat_name = item.get('category', 'Unknown')
                            cat_spent = item.get('spent', 0)
                            if cat_spent > 0:
                                category_breakdown[cat_name] = cat_spent
                    
                    transaction_summary = {
                        'total_spend': total.get('total', 0),
                        'monthly_spend': monthly.get('recent_monthly', {}).get('total', 0) if monthly else 0,
                        'top_categories': [cat.get('category') for cat in categories.get('items', [])[:5]],
                        'category_breakdown': category_breakdown,
                        'savings_rate': 0  # Calculate if income data available
                    }
                    
                    # Perform financial health analysis if analysis agent is available
                    if self.analysis_agent:
                        try:
                            # Load user profile for income/savings goals
                            import json
                            profile_path = os.path.join(
                                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                'state', 'profile.json'
                            )
                            profile = {}
                            if os.path.exists(profile_path):
                                with open(profile_path, 'r') as f:
                                    profile = json.load(f)
                            
                            # Extract financial data
                            financial_data = self.analysis_agent.extract_financial_data_from_transactions(
                                transaction_summary, profile
                            )
                            
                            # Perform analysis (with user_id for personalization)
                            financial_analysis = self.analysis_agent.analyze(financial_data, user_id=user_id)
                        except Exception as e:
                            print(f"Financial analysis error: {e}")
                            
                except Exception as e:
                    print(f"Error getting transaction summary: {e}")
            
            # Step 4: Determine if this is a strategy/investment query
            query_type = parsed.get('query_type', '')
            is_investment_query = query_type in ['investment_advice', 'portfolio_question', 'market_question']
            
            if is_investment_query and knowledge_context:
                # Step 5: Strategy Agent - Generate strategy
                risk_profile = self.risk_agent.get_risk_profile()
                strategy = self.strategy_agent.generate_strategy(
                    user_query=message,
                    knowledge_context=knowledge_context,
                    risk_profile=risk_profile,
                    transaction_summary=transaction_summary,
                    market_context=None  # Could fetch real-time market data here
                )
                
                # Step 6: Risk Agent - Assess risk alignment
                risk_assessment = self.risk_agent.assess_risk(
                    strategy=strategy,
                    risk_profile=risk_profile,
                    knowledge_context=knowledge_context
                )
                
                # Step 7: Implementation Agent - Generate execution plan
                implementation_plan = None
                if self.implementation_agent:
                    try:
                        risk_tolerance = risk_profile.get("risk_tolerance", "Moderate")
                        recommendations = risk_assessment.get('adjusted_recommendations') or strategy.get('recommendations', [])
                        
                        # Extract specific products if mentioned in strategy
                        recommended_assets = []
                        for rec in recommendations:
                            if rec.get("specific_products"):
                                recommended_assets.extend(rec.get("specific_products", []))
                        
                        if recommendations:
                            implementation_plan = self.implementation_agent.generate_implementation_plan(
                                risk_profile=risk_tolerance,
                                allocation=recommendations,
                                recommended_assets=recommended_assets if recommended_assets else None
                            )
                    except Exception as e:
                        print(f"Implementation plan generation error: {e}")
                
                # Step 8: Output Agent - Format response
                response = self.output_agent.format_response(
                    user_query=message,
                    strategy=strategy,
                    risk_assessment=risk_assessment,
                    transaction_insights=transaction_summary,
                    knowledge_sources=knowledge_context
                )
                
                # Add financial analysis if available
                if financial_analysis:
                    response["financial_analysis"] = financial_analysis
                    response["type"] = "strategy_with_analysis"
                
                # Add implementation plan if available
                if implementation_plan:
                    # Format implementation plan into response
                    impl_response = self.implementation_agent.format_implementation_response(implementation_plan)
                    response["implementation_plan"] = impl_response["data"]
                    # Append implementation plan to answer
                    response["answer"] += "\n\n---\n\n" + impl_response["answer"]
                    if response["type"] == "strategy_with_analysis":
                        response["type"] = "strategy_with_analysis_and_implementation"
                    else:
                        response["type"] = "strategy_with_implementation"
                
                return response
            else:
                # For non-investment queries, use knowledge context but simpler output
                data_analysis, visualizations = self._get_comprehensive_data_context(message, user_id=user_id)
                
                # Build prompt with knowledge context
                full_prompt = f"{system_advisor}\n\n"
                
                if knowledge_context:
                    knowledge_text = "RELEVANT KNOWLEDGE:\n"
                    for i, chunk in enumerate(knowledge_context[:3], 1):
                        knowledge_text += f"\n[{i}] {chunk.get('content', '')}\n"
                    full_prompt += f"{knowledge_text}\n\n"
                
                if data_analysis:
                    full_prompt += f"TRANSACTION DATA CONTEXT:\n{data_analysis}\n\n"
                
                full_prompt += f"User Question: {message}\n\n"
                
                # Get response from LLM
                response_text = self.llm_client.complete(full_prompt)
                
                # Format with Output Agent
                response = self.output_agent.format_simple_response(
                    answer=response_text,
                    knowledge_sources=knowledge_context
                )
                
                # Add visualizations if available
                if visualizations:
                    response["visualizations"] = visualizations
                    response["type"] = "visualization"
                
                # Add financial analysis if available
                if financial_analysis:
                    response["financial_analysis"] = financial_analysis
                    if response["type"] == "visualization":
                        response["type"] = "visualization_with_analysis"
                    else:
                        response["type"] = "analysis"
                
                return response
                
        except Exception as e:
            # Fallback to original workflow on error
            print(f"VectorDB workflow error: {e}")
            return None
    
    def chat(self, message: str, context: List[Dict[str, str]] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Main chat function that processes user messages and returns structured responses
        Uses VectorDB workflow if available, otherwise falls back to original workflow
        
        Args:
            message: User's message
            context: Conversation context
            user_id: Optional user ID for personalization
        """
        try:
            # Try VectorDB workflow first if available
            if self.use_vectordb:
                vectordb_response = self._process_with_vectordb_workflow(message, context, user_id=user_id)
                if vectordb_response:
                    return vectordb_response
            
            # Fallback to original workflow
            # Build context from previous messages (limit to last 5 to avoid repetition)
            context_str = ""
            if context:
                recent_context = context[-5:]  # Only keep last 5 messages
                context_str = "\n".join([f"{msg.get('role', 'user')}: {msg.get('content', '')}" for msg in recent_context])
            
            # Get comprehensive data context
            data_analysis, visualizations = self._get_comprehensive_data_context(message, user_id=user_id)
            
            # Create the full prompt with rich data context
            full_prompt = f"{system_advisor}\n\n"
            
            if data_analysis:
                full_prompt += f"TRANSACTION DATA CONTEXT:\n{data_analysis}\n\n"
            
            full_prompt += f"User Question: {message}\n\n"
            
            if context_str:
                full_prompt += f"Recent conversation:\n{context_str}\n\n"
            
            # Add instructions for faster, more focused responses
            full_prompt += """INSTRUCTIONS:
- Provide concise, data-driven answers with specific numbers
- Be direct and to the point - avoid lengthy explanations
- Use bullet points for multiple items
- If visualizations are available, mention them briefly
- Don't repeat greetings if continuing a conversation
- Focus on the most relevant data points"""
            
            # Get response from LLM
            response = self.llm_client.complete(full_prompt)
            
            # Prepare response with visualizations
            response_data = {
                "answer": response,
                "status": "success",
                "type": "text"
            }
            
            # Add visualizations if available
            if visualizations:
                response_data["visualizations"] = visualizations
                response_data["type"] = "visualization"
            
            # Try to parse as JSON first, fallback to text
            try:
                # Try to extract JSON from response
                json_response = validate_json_response(response)
                response_data["answer"] = json_response.get("answer", response)
                response_data["type"] = "json"
                response_data["data"] = json_response
            except:
                # Keep the text response as is
                pass
            
            return response_data
                
        except Exception as e:
            return {
                "answer": f"I apologize, but I encountered an error: {str(e)}",
                "status": "error",
                "type": "error"
            }

# Create global instance
enhanced_orchestrator = EnhancedOrchestrator()

def chat(message: str, context: List[Dict[str, str]] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Main chat function that can be imported by other modules
    """
    return enhanced_orchestrator.chat(message, context, user_id=user_id)

def craft_answer(user_message: str, observations_text: str = "") -> str:
    """
    Convenience function for backward compatibility with advisor_reply.py
    """
    return enhanced_orchestrator.craft_advisor_reply(user_message, observations_text)
