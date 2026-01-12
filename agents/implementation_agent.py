"""
Implementation Agent: Converts investment strategies into actionable execution steps
"""
from typing import Dict, Any, List, Optional


class ImplementationAgent:
    """
    Converts investment strategy recommendations into clear, step-by-step execution plans
    with specific fund names, platforms, and instructions
    """
    
    # Popular investment platforms in India
    PLATFORMS = {
        "mutual_funds": ["Groww", "Zerodha", "Kuvera", "Paytm Money", "ET Money", "HDFC Securities"],
        "etf": ["Zerodha", "Groww", "Upstox", "ICICI Direct", "HDFC Securities"],
        "gold": ["Groww", "Zerodha", "Paytm Money", "SBI Gold ETF", "HDFC Gold ETF"],
        "fd": ["Bank websites", "Bank mobile apps", "CRED", "Groww", "Paytm Money"]
    }
    
    # Popular fund suggestions by category (examples - can be expanded)
    FUND_SUGGESTIONS = {
        "large_cap": [
            "HDFC Top 100 Fund - Direct Growth",
            "ICICI Prudential Bluechip Fund - Direct Growth",
            "SBI Bluechip Fund - Direct Growth",
            "Nippon India Large Cap Fund - Direct Growth"
        ],
        "mid_cap": [
            "HDFC Mid-Cap Opportunities Fund - Direct Growth",
            "SBI Magnum Midcap Fund - Direct Growth",
            "ICICI Prudential Midcap Fund - Direct Growth"
        ],
        "small_cap": [
            "HDFC Small Cap Fund - Direct Growth",
            "SBI Small Cap Fund - Direct Growth",
            "Nippon India Small Cap Fund - Direct Growth"
        ],
        "index_fund": [
            "HDFC Index Fund - Nifty 50 Plan - Direct Growth",
            "ICICI Prudential Nifty Index Fund - Direct Growth",
            "UTI Nifty Index Fund - Direct Growth"
        ],
        "etf": [
            "Nippon India ETF Nifty BeES",
            "ICICI Prudential Nifty ETF",
            "HDFC Nifty 50 ETF",
            "SBI Nifty ETF"
        ],
        "debt": [
            "HDFC Short Term Debt Fund - Direct Growth",
            "ICICI Prudential Short Term Fund - Direct Growth",
            "SBI Magnum Gilt Fund - Direct Growth"
        ],
        "hybrid": [
            "HDFC Balanced Advantage Fund - Direct Growth",
            "ICICI Prudential Balanced Advantage Fund - Direct Growth",
            "SBI Balanced Advantage Fund - Direct Growth"
        ],
        "gold": [
            "SBI Gold ETF",
            "HDFC Gold ETF",
            "ICICI Prudential Gold ETF",
            "Nippon India Gold ETF"
        ]
    }
    
    def generate_implementation_plan(
        self,
        risk_profile: str,
        allocation: List[Dict[str, Any]],
        recommended_assets: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generate step-by-step implementation plan
        
        Args:
            risk_profile: "Safe", "Moderate", or "Aggressive"
            allocation: List of dicts with keys: category, allocation_percentage, rationale
            recommended_assets: Optional list of specific fund names
        
        Returns:
            Dict with implementation plan
        """
        # Normalize risk profile
        risk_profile = risk_profile.lower().capitalize()
        if risk_profile not in ["Safe", "Moderate", "Aggressive"]:
            risk_profile = "Moderate"  # Default
        
        # Build implementation plan
        plan = {
            "risk_profile": risk_profile,
            "short_explanation": self._generate_short_explanation(risk_profile, allocation),
            "action_plan": self._generate_action_plan(allocation, recommended_assets),
            "platform_suggestions": self._suggest_platforms(allocation),
            "sip_vs_lumpsum": self._suggest_sip_vs_lumpsum(risk_profile, allocation)
        }
        
        return plan
    
    def _generate_short_explanation(
        self,
        risk_profile: str,
        allocation: List[Dict[str, Any]]
    ) -> str:
        """Generate a short, beginner-friendly explanation"""
        total_allocation = sum(rec.get("allocation_percentage", 0) for rec in allocation)
        
        explanation = f"Based on your {risk_profile} risk profile, here's your investment plan:\n\n"
        explanation += "Your portfolio is divided into:\n"
        
        for rec in allocation:
            category = rec.get("category", "Unknown")
            percentage = rec.get("allocation_percentage", 0)
            rationale = rec.get("rationale", "")
            
            explanation += f"• **{category}**: {percentage}%"
            if rationale:
                explanation += f" - {rationale}"
            explanation += "\n"
        
        if total_allocation < 100:
            explanation += f"\n*Note: Total allocation is {total_allocation}%. Consider allocating the remaining {100-total_allocation}% to emergency fund or savings.*\n"
        
        return explanation
    
    def _generate_action_plan(
        self,
        allocation: List[Dict[str, Any]],
        recommended_assets: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Generate step-by-step action plan"""
        steps = []
        step_num = 1
        
        # Step 1: KYC and Account Setup
        steps.append({
            "step": step_num,
            "title": "Complete KYC (Know Your Customer)",
            "description": "You need to complete KYC before investing. This is a one-time process.",
            "instructions": [
                "Choose a platform (we'll suggest options below)",
                "Download the app or visit the website",
                "Sign up with your PAN card, Aadhaar, and bank details",
                "Complete e-KYC (usually takes 5-10 minutes)",
                "Link your bank account"
            ],
            "estimated_time": "10-15 minutes"
        })
        step_num += 1
        
        # Steps for each allocation category
        for rec in allocation:
            category = rec.get("category", "Unknown")
            percentage = rec.get("allocation_percentage", 0)
            
            # Get specific fund suggestions
            fund_name = self._get_fund_suggestion(category, recommended_assets)
            
            steps.append({
                "step": step_num,
                "title": f"Invest {percentage}% in {category}",
                "description": f"Allocate {percentage}% of your investment amount to {category} funds.",
                "fund_suggestion": fund_name,
                "instructions": self._get_category_instructions(category, fund_name),
                "estimated_time": "5-10 minutes per fund"
            })
            step_num += 1
        
        # Final step: Review and Monitor
        steps.append({
            "step": step_num,
            "title": "Set Up Regular Monitoring",
            "description": "Review your portfolio periodically to ensure it stays aligned with your goals.",
            "instructions": [
                "Check your portfolio once a month",
                "Review performance quarterly",
                "Rebalance if allocation drifts by more than 5%",
                "Continue SIPs as planned"
            ],
            "estimated_time": "Ongoing"
        })
        
        return steps
    
    def _get_fund_suggestion(
        self,
        category: str,
        recommended_assets: Optional[List[str]] = None
    ) -> str:
        """Get specific fund name for category"""
        # If specific assets are recommended, use them
        if recommended_assets:
            # Try to match category with recommended assets
            category_lower = category.lower()
            for asset in recommended_assets:
                if any(keyword in asset.lower() for keyword in category_lower.split()):
                    return asset
            # If no match, return first recommended asset
            return recommended_assets[0]
        
        # Otherwise, suggest based on category
        category_mapping = {
            "equity": "large_cap",
            "large cap": "large_cap",
            "large-cap": "large_cap",
            "mid cap": "mid_cap",
            "mid-cap": "mid_cap",
            "small cap": "small_cap",
            "small-cap": "small_cap",
            "index": "index_fund",
            "index fund": "index_fund",
            "etf": "etf",
            "debt": "debt",
            "fixed deposit": "fd",
            "fd": "fd",
            "gold": "gold",
            "hybrid": "hybrid",
            "balanced": "hybrid"
        }
        
        fund_type = "large_cap"  # Default
        for key, value in category_mapping.items():
            if key in category.lower():
                fund_type = value
                break
        
        funds = self.FUND_SUGGESTIONS.get(fund_type, self.FUND_SUGGESTIONS["large_cap"])
        return funds[0] if funds else "Consult with a financial advisor"
    
    def _get_category_instructions(
        self,
        category: str,
        fund_name: str
    ) -> List[str]:
        """Get step-by-step instructions for investing in a category"""
        category_lower = category.lower()
        
        if "etf" in category_lower or "exchange traded" in category_lower:
            return [
                f"Search for '{fund_name}' in the app",
                "Click 'Buy' or 'Invest'",
                "Enter the amount you want to invest",
                "Choose 'Market Order' (executes immediately) or 'Limit Order' (executes at your price)",
                "Review and confirm the order",
                "The ETF units will be credited to your Demat account"
            ]
        elif "gold" in category_lower:
            return [
                f"Search for '{fund_name}' or 'Gold ETF'",
                "Click 'Invest' or 'Buy'",
                "Enter investment amount",
                "Choose SIP (recommended) or Lumpsum",
                "Set up auto-debit if doing SIP",
                "Confirm the transaction"
            ]
        elif "fd" in category_lower or "fixed deposit" in category_lower:
            return [
                "Open your bank's mobile app or website",
                "Navigate to 'Fixed Deposit' or 'FD' section",
                "Click 'Open New FD'",
                "Enter the amount and tenure (recommended: 1-3 years)",
                "Choose interest payout frequency (monthly/quarterly/at maturity)",
                "Review terms and confirm"
            ]
        else:  # Mutual funds
            return [
                f"Search for '{fund_name}' in the investment app",
                "Click on the fund name to see details",
                "Click 'Invest' or 'Start SIP'",
                "Enter the investment amount",
                "Choose 'Direct Plan - Growth' (lower fees)",
                "Select SIP frequency (monthly recommended) or Lumpsum",
                "Set up auto-debit from your bank account (for SIP)",
                "Review all details and confirm"
            ]
    
    def _suggest_platforms(
        self,
        allocation: List[Dict[str, Any]]
    ) -> Dict[str, List[str]]:
        """Suggest platforms based on allocation categories"""
        categories = [rec.get("category", "").lower() for rec in allocation]
        
        suggested_platforms = {
            "mutual_funds": [],
            "etf": [],
            "general": []
        }
        
        # Determine what types of investments
        has_etf = any("etf" in cat or "exchange traded" in cat for cat in categories)
        has_mf = any("equity" in cat or "mutual" in cat or "fund" in cat for cat in categories if "etf" not in cat)
        has_gold = any("gold" in cat for cat in categories)
        
        if has_mf or has_gold:
            suggested_platforms["mutual_funds"] = self.PLATFORMS["mutual_funds"][:3]
        
        if has_etf:
            suggested_platforms["etf"] = self.PLATFORMS["etf"][:3]
        
        # General recommendation
        suggested_platforms["general"] = ["Groww", "Zerodha", "Kuvera"]
        
        return suggested_platforms
    
    def _suggest_sip_vs_lumpsum(
        self,
        risk_profile: str,
        allocation: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Suggest SIP vs Lumpsum based on risk profile and allocation"""
        # Calculate equity exposure
        equity_categories = ["equity", "large cap", "mid cap", "small cap", "index", "etf"]
        equity_percentage = sum(
            rec.get("allocation_percentage", 0)
            for rec in allocation
            if any(cat in rec.get("category", "").lower() for cat in equity_categories)
        )
        
        suggestion = {
            "recommendation": "SIP (Systematic Investment Plan)",
            "reason": "",
            "sip_details": {
                "frequency": "Monthly",
                "start_date": "1st or 15th of each month",
                "benefits": [
                    "Reduces impact of market volatility",
                    "Builds investment discipline",
                    "Averages out purchase price",
                    "Requires smaller initial capital"
                ]
            },
            "lumpsum_details": {
                "when_to_use": [
                    "You have a large amount ready (bonus, tax refund)",
                    "Market is in a correction phase",
                    "You're comfortable with timing the market"
                ],
                "considerations": [
                    "Higher risk if market falls immediately after investment",
                    "Requires larger initial capital",
                    "Better for experienced investors"
                ]
            }
        }
        
        if risk_profile == "Safe":
            suggestion["reason"] = "SIP is safer as it spreads risk over time. Perfect for conservative investors."
        elif risk_profile == "Moderate":
            suggestion["reason"] = "SIP helps moderate investors build wealth gradually while managing risk."
            suggestion["lumpsum_details"]["when_to_use"].append("Consider 70% SIP + 30% Lumpsum for balance")
        else:  # Aggressive
            suggestion["reason"] = "Even aggressive investors benefit from SIP discipline. Consider 60% SIP + 40% Lumpsum if you have capital ready."
            suggestion["lumpsum_details"]["when_to_use"].append("You can take advantage of market dips with lumpsum")
        
        if equity_percentage > 60:
            suggestion["sip_details"]["benefits"].append("Especially important for high equity exposure")
        
        return suggestion
    
    def format_implementation_response(
        self,
        implementation_plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Format implementation plan into user-friendly response"""
        response_parts = []
        
        # Short Explanation
        response_parts.append("## 📋 Your Investment Implementation Plan\n")
        response_parts.append(implementation_plan["short_explanation"])
        response_parts.append("\n---\n")
        
        # SIP vs Lumpsum Suggestion
        sip_info = implementation_plan["sip_vs_lumpsum"]
        response_parts.append("## 💡 SIP vs Lumpsum Recommendation\n")
        response_parts.append(f"**Recommendation:** {sip_info['recommendation']}\n")
        response_parts.append(f"**Why:** {sip_info['reason']}\n\n")
        response_parts.append("**SIP Benefits:**\n")
        for benefit in sip_info["sip_details"]["benefits"]:
            response_parts.append(f"• {benefit}\n")
        response_parts.append(f"\n**SIP Frequency:** {sip_info['sip_details']['frequency']}\n")
        response_parts.append(f"**Start Date:** {sip_info['sip_details']['start_date']}\n")
        response_parts.append("\n---\n")
        
        # Action Plan
        response_parts.append("## 📝 Step-by-Step Action Plan\n\n")
        for step in implementation_plan["action_plan"]:
            response_parts.append(f"### Step {step['step']}: {step['title']}\n")
            response_parts.append(f"{step['description']}\n\n")
            
            if step.get("fund_suggestion"):
                response_parts.append(f"**Suggested Fund:** {step['fund_suggestion']}\n\n")
            
            response_parts.append("**Instructions:**\n")
            for i, instruction in enumerate(step["instructions"], 1):
                response_parts.append(f"{i}. {instruction}\n")
            
            if step.get("estimated_time"):
                response_parts.append(f"\n*Estimated time: {step['estimated_time']}*\n")
            
            response_parts.append("\n")
        
        # Platform Suggestions
        platforms = implementation_plan["platform_suggestions"]
        response_parts.append("## 🏪 Platform Suggestions\n\n")
        response_parts.append("**Recommended Platforms:**\n")
        for platform in platforms.get("general", []):
            response_parts.append(f"• **{platform}** - User-friendly, low fees, good for beginners\n")
        
        if platforms.get("mutual_funds"):
            response_parts.append("\n**For Mutual Funds:**\n")
            for platform in platforms["mutual_funds"]:
                response_parts.append(f"• {platform}\n")
        
        if platforms.get("etf"):
            response_parts.append("\n**For ETFs:**\n")
            for platform in platforms["etf"]:
                response_parts.append(f"• {platform}\n")
        
        response_parts.append("\n*Note: All platforms are regulated by SEBI. Choose based on your comfort and features you need.*\n")
        
        # Combine into final response
        final_answer = "".join(response_parts)
        
        return {
            "answer": final_answer,
            "status": "success",
            "type": "implementation_plan",
            "data": implementation_plan
        }

