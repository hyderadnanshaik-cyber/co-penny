"""
Utility script to populate VectorDB with financial knowledge
Run this to seed the knowledge base with initial content
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vectordb.knowledge_store import get_knowledge_store


def populate_sample_knowledge():
    """Populate VectorDB with sample financial knowledge"""
    knowledge_store = get_knowledge_store()
    
    print("📚 Populating VectorDB with financial knowledge...\n")
    
    # Sample Market Insights
    print("Adding market insights...")
    knowledge_store.store_market_insight(
        title="Indian Equity Market Overview 2024",
        content="""
        The Indian equity market has shown resilience in 2024, with the Nifty 50 and Sensex 
        reaching new highs. Key factors driving growth include:
        
        - Strong domestic consumption driven by rising middle-class income
        - Government infrastructure spending and policy reforms
        - FII (Foreign Institutional Investor) inflows returning to positive territory
        - Corporate earnings growth across sectors
        
        Investment themes to watch:
        - Manufacturing and Make in India initiatives
        - Green energy and sustainability
        - Digital economy and fintech
        - Healthcare and pharmaceuticals
        
        Risk factors:
        - Global economic slowdown impact on exports
        - Inflation concerns and RBI policy changes
        - Geopolitical tensions affecting commodity prices
        """,
        date="2024-01-15",
        source="Market Research"
    )
    
    # Investment Strategies
    print("Adding investment strategies...")
    knowledge_store.store_strategy(
        title="Systematic Investment Plan (SIP) Strategy",
        content="""
        SIP is one of the most effective ways to build wealth over the long term.
        
        Key Benefits:
        - Rupee cost averaging: Buy more units when prices are low, fewer when high
        - Disciplined investing: Automatic monthly investments
        - Power of compounding: Long-term wealth creation
        - Flexibility: Start with as little as ₹500/month
        
        Recommended Allocation:
        - For conservative investors: 60% Debt, 30% Equity, 10% Hybrid
        - For moderate investors: 40% Large-cap, 30% Mid-cap, 20% Small-cap, 10% Debt
        - For aggressive investors: 50% Mid-cap, 30% Small-cap, 20% Large-cap
        
        Best Practices:
        - Invest for at least 5-7 years to see meaningful returns
        - Increase SIP amount by 10% annually
        - Review and rebalance portfolio annually
        - Don't stop SIP during market downturns
        """,
        strategy_type="SIP",
        risk_level="moderate"
    )
    
    knowledge_store.store_strategy(
        title="Asset Allocation by Age",
        content="""
        Asset allocation should change based on your age and life stage.
        
        Age 20-30 (Early Career):
        - 80% Equity, 20% Debt
        - Focus on growth and wealth creation
        - Can take higher risks
        - Invest in diversified equity mutual funds
        
        Age 30-40 (Mid Career):
        - 70% Equity, 30% Debt
        - Balance growth with stability
        - Start building emergency fund (6 months expenses)
        - Consider tax-saving investments (ELSS)
        
        Age 40-50 (Pre-Retirement):
        - 60% Equity, 40% Debt
        - Focus on capital preservation
        - Increase debt allocation gradually
        - Plan for retirement corpus
        
        Age 50+ (Near Retirement):
        - 40% Equity, 60% Debt
        - Capital preservation priority
        - Regular income generation
        - Consider annuity products
        """,
        strategy_type="Asset Allocation",
        risk_level="moderate"
    )
    
    # Risk Profile Guidance
    print("Adding risk profile guidance...")
    knowledge_store.store_risk_guidance(
        title="Conservative Risk Profile Investment Guide",
        risk_profile="conservative",
        content="""
        For conservative investors, capital preservation is the primary goal.
        
        Recommended Investments:
        - 60-70% in Debt instruments (FDs, Debt Mutual Funds, Government Bonds)
        - 20-30% in Equity (Large-cap funds, Blue-chip stocks)
        - 10% in Gold and other safe-haven assets
        
        Products to Consider:
        - Fixed Deposits (FDs) for guaranteed returns
        - Debt Mutual Funds for better tax efficiency
        - Large-cap Equity Mutual Funds for equity exposure
        - Public Provident Fund (PPF) for long-term tax savings
        - Senior Citizens Savings Scheme (SCSS) if eligible
        
        Avoid:
        - High-risk equity investments
        - Small-cap and mid-cap funds
        - Derivatives and futures trading
        - Cryptocurrency and speculative investments
        
        Expected Returns: 6-8% annually
        Risk Level: Low
        Time Horizon: Short to medium term (1-5 years)
        """
    )
    
    knowledge_store.store_risk_guidance(
        title="Moderate Risk Profile Investment Guide",
        risk_profile="moderate",
        content="""
        Moderate investors seek a balance between growth and stability.
        
        Recommended Investments:
        - 50-60% in Equity (Mix of Large-cap, Mid-cap, and Small-cap)
        - 30-40% in Debt (Debt Mutual Funds, FDs)
        - 10% in Hybrid funds
        
        Products to Consider:
        - Balanced Advantage Funds
        - Multi-cap Equity Mutual Funds
        - Large and Mid-cap Funds
        - Debt Mutual Funds
        - ELSS for tax savings
        - Gold ETFs for diversification
        
        Portfolio Structure:
        - 40% Large-cap funds
        - 30% Mid-cap funds
        - 20% Debt funds
        - 10% Small-cap funds
        
        Expected Returns: 10-12% annually
        Risk Level: Medium
        Time Horizon: Medium to long term (5-10 years)
        """
    )
    
    knowledge_store.store_risk_guidance(
        title="Aggressive Risk Profile Investment Guide",
        risk_profile="aggressive",
        content="""
        Aggressive investors prioritize wealth creation and can tolerate volatility.
        
        Recommended Investments:
        - 70-80% in Equity (Focus on Mid-cap and Small-cap)
        - 10-20% in Debt (for stability)
        - 10% in Alternative investments
        
        Products to Consider:
        - Small-cap Equity Mutual Funds
        - Mid-cap Equity Mutual Funds
        - Sector-specific funds (Technology, Healthcare, etc.)
        - Direct equity investments in growth stocks
        - International equity funds for diversification
        
        Portfolio Structure:
        - 30% Large-cap funds
        - 40% Mid-cap funds
        - 20% Small-cap funds
        - 10% Debt funds
        
        Risk Management:
        - Diversify across sectors
        - Regular portfolio review
        - Set stop-losses for direct equity
        - Maintain emergency fund
        
        Expected Returns: 12-15%+ annually
        Risk Level: High
        Time Horizon: Long term (10+ years)
        """
    )
    
    # General Financial Education
    print("Adding general financial knowledge...")
    knowledge_store.store_document(
        title="Mutual Fund Basics",
        content="""
        Mutual funds pool money from multiple investors to invest in a diversified portfolio.
        
        Types of Mutual Funds:
        1. Equity Funds: Invest primarily in stocks
           - Large-cap: Top 100 companies by market cap
           - Mid-cap: Companies ranked 101-250
           - Small-cap: Companies ranked 251+
           - Multi-cap: Mix of all market caps
        
        2. Debt Funds: Invest in fixed-income securities
           - Liquid funds: Very short-term (up to 91 days)
           - Short-term: 1-3 years
           - Long-term: 3+ years
        
        3. Hybrid Funds: Mix of equity and debt
           - Balanced: 60-70% equity, 30-40% debt
           - Aggressive Hybrid: 65-80% equity
           - Conservative Hybrid: 20-35% equity
        
        Key Metrics:
        - NAV (Net Asset Value): Price per unit
        - Expense Ratio: Annual fees (typically 0.5-2.5%)
        - AUM (Assets Under Management): Total fund size
        - Returns: Historical performance (not guaranteed)
        
        Tax Implications:
        - Equity funds: 15% STCG (if held <1 year), 10% LTCG (if >1L gains, held >1 year)
        - Debt funds: As per income tax slab
        - ELSS: Tax deduction up to ₹1.5L under Section 80C, 3-year lock-in
        """,
        namespace="general",
        metadata={"type": "education", "category": "mutual_funds"}
    )
    
    knowledge_store.store_document(
        title="Emergency Fund Planning",
        content="""
        An emergency fund is crucial for financial security.
        
        Purpose:
        - Cover unexpected expenses (medical, job loss, repairs)
        - Avoid debt during emergencies
        - Provide peace of mind
        
        How Much to Save:
        - Minimum: 3 months of expenses
        - Recommended: 6 months of expenses
        - For self-employed: 9-12 months
        
        Where to Keep:
        - Liquid funds: Easy access, better returns than savings account
        - High-yield savings account: Immediate access
        - Fixed deposits: Slightly higher returns, partial liquidity
        
        Building Strategy:
        - Start with small monthly contributions
        - Automate transfers to emergency fund
        - Replenish after using funds
        - Review and adjust based on life changes
        
        What Counts as Emergency:
        - Medical emergencies
        - Job loss
        - Major home/car repairs
        - Unexpected family needs
        
        What Doesn't Count:
        - Planned purchases
        - Investment opportunities
        - Vacation expenses
        - Shopping
        """,
        namespace="general",
        metadata={"type": "education", "category": "emergency_fund"}
    )
    
    print("\n✅ Knowledge base populated successfully!")
    print("\nYou can now query the VectorDB for financial advice.")
    print("Example queries:")
    print("  - 'What is a good SIP strategy?'")
    print("  - 'How should I invest based on my risk profile?'")
    print("  - 'Tell me about mutual funds'")


if __name__ == "__main__":
    populate_sample_knowledge()

