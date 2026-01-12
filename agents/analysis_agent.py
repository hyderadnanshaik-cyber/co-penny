"""
Analysis Agent: ML + Rule-based financial health analysis with visualizations
"""
import os
from typing import Dict, Any, Optional
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
plt.style.use('dark_background')


class AnalysisAgent:
    """
    Performs ML-based financial health analysis with visualizations
    Uses trained model if available, otherwise uses rule-based analysis
    """
    
    def __init__(self, model_path: Optional[str] = None, user_id: Optional[str] = None):
        """
        Initialize Analysis Agent
        
        Args:
            model_path: Path to trained ML model (financial_model.pkl)
                       If None, looks in state/models/financial_model.pkl
            user_id: Optional user ID for personalized models
        """
        self.model = None
        self.user_id = user_id
        self.model_path = model_path or self._get_default_model_path()
        self._load_model()
    
    def _get_default_model_path(self) -> str:
        """Get default model path"""
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        # If user_id is provided, try to use user-specific model first
        if self.user_id:
            user_model_path = self._get_user_model_path(self.user_id)
            if user_model_path and os.path.exists(user_model_path):
                return user_model_path
        return os.path.join(base_dir, "state", "models", "financial_model.pkl")
    
    def _get_user_model_path(self, user_id: str) -> Optional[str]:
        """Get path to user-specific model"""
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(base_dir, "state", "models", "users", f"{user_id}_model.pkl")
    
    def _load_model(self):
        """Load ML model if available"""
        try:
            if os.path.exists(self.model_path):
                import joblib
                self.model = joblib.load(self.model_path)
                print(f"✅ Loaded financial health model from {self.model_path}")
            else:
                print(f"ℹ️  ML model not found at {self.model_path}. Using rule-based analysis.")
        except Exception as e:
            print(f"⚠️  Could not load ML model: {e}. Using rule-based analysis.")
            self.model = None
    
    def analyze(
        self,
        financial_data: Dict[str, Any],
        strategy_data: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Perform financial health analysis
        
        Args:
            financial_data: Dict with keys:
                - income: float
                - savings_goal: float
                - expenses: Dict[str, float] (category -> amount)
            strategy_data: Optional dict with suggested_values for comparison
            user_id: Optional user ID for personalized model (overrides instance user_id)
        
        Returns:
            Dict with analysis results and visualizations
        """
        # Use provided user_id or fall back to instance user_id
        effective_user_id = user_id or self.user_id
        
        # Try to load user-specific model if user_id is provided
        model_to_use = self.model
        if effective_user_id and not model_to_use:
            user_model_path = self._get_user_model_path(effective_user_id)
            if user_model_path and os.path.exists(user_model_path):
                try:
                    import joblib
                    model_to_use = joblib.load(user_model_path)
                except Exception as e:
                    print(f"Could not load user model: {e}")
        
        income = financial_data.get("income", 0)
        savings_goal = financial_data.get("savings_goal", 0)
        expenses = financial_data.get("expenses", {})
        
        total_expenses = sum(expenses.values()) if isinstance(expenses, dict) else 0
        surplus = income - total_expenses
        goal_gap = surplus - savings_goal
        
        # Predict financial health using ML model or rule-based
        if model_to_use:
            try:
                features = [[income, total_expenses, savings_goal, surplus]]
                prediction = model_to_use.predict(features)[0]
            except Exception as e:
                print(f"ML prediction error: {e}")
                prediction = self._rule_based_prediction(income, total_expenses, savings_goal, surplus)
        else:
            prediction = self._rule_based_prediction(income, total_expenses, savings_goal, surplus)
        
        insights = []
        if prediction == "Bad":
            insights.append("⚠️ Financial health is poor. Expenses exceed savings target.")
        elif prediction == "At Risk":
            insights.append("⚠️ Financial health is at risk. Surplus is low compared to savings goal.")
        else:
            insights.append("✅ Financial health is good. You are meeting savings goals.")
        
        analysis = {
            "income": income,
            "total_expenses": total_expenses,
            "surplus": surplus,
            "savings_goal": savings_goal,
            "extra_surplus": goal_gap,
            "financial_health": prediction,
            "insights": insights
        }
        
        # Generate visualizations
        bar_chart, pie_chart = self._generate_visualizations(
            income, total_expenses, savings_goal, surplus, expenses, strategy_data
        )
        
        analysis["bar_chart"] = bar_chart
        analysis["pie_chart"] = pie_chart
        
        return analysis
    
    def _rule_based_prediction(
        self,
        income: float,
        total_expenses: float,
        savings_goal: float,
        surplus: float
    ) -> str:
        """Rule-based financial health prediction (fallback when ML model not available)"""
        if total_expenses > income:
            return "Bad"
        elif surplus < savings_goal * 0.5:  # Less than 50% of goal
            return "At Risk"
        elif surplus < savings_goal:
            return "At Risk"
        else:
            return "Good"
    
    def _generate_visualizations(
        self,
        income: float,
        total_expenses: float,
        savings_goal: float,
        surplus: float,
        expenses: Dict[str, float],
        strategy_data: Optional[Dict[str, Any]] = None
    ):
        """Generate bar chart and pie chart visualizations"""
        # Bar chart (with or without comparison)
        if strategy_data and strategy_data.get("suggested_values"):
            # Comparison bar chart
            fig_bar, ax1 = plt.subplots(figsize=(12, 6))
            fig_bar.patch.set_alpha(0)
            ax1.patch.set_alpha(0)
            
            categories = ["Income", "Expenses", "Savings Goal", "Surplus"]
            current_values = [income, total_expenses, savings_goal, surplus]
            suggested = strategy_data["suggested_values"]
            suggested_values = [
                suggested.get("income", income),
                suggested.get("expenses", total_expenses),
                suggested.get("savings_goal", savings_goal),
                suggested.get("surplus", surplus)
            ]
            
            x = range(len(categories))
            width = 0.35
            
            bars1 = ax1.bar([i - width/2 for i in x], current_values, width,
                           color=['green', 'red', 'blue', 'orange'], alpha=0.7, label='Current')
            bars2 = ax1.bar([i + width/2 for i in x], suggested_values, width,
                           color=['lightgreen', 'lightcoral', 'lightblue', 'moccasin'], 
                           alpha=0.7, label='Suggested')
            
            ax1.set_xlabel('Financial Categories', color='white')
            ax1.set_ylabel('Amount (₹)', color='white')
            ax1.set_title('Current vs Suggested Financial Strategy Comparison', color='white')
            ax1.set_xticks(x)
            ax1.set_xticklabels(categories, color='white')
            ax1.legend()
            ax1.tick_params(colors='white')
            
            # Add value labels on bars
            for bars in [bars1, bars2]:
                for bar in bars:
                    height = bar.get_height()
                    ax1.text(bar.get_x() + bar.get_width()/2., height,
                            f'₹{int(height):,}', ha='center', va='bottom', fontsize=8, color='white')
            
            plt.tight_layout()
        else:
            # Single bar chart
            fig_bar, ax1 = plt.subplots(figsize=(10, 6))
            fig_bar.patch.set_alpha(0)
            ax1.patch.set_alpha(0)
            
            categories = ["Income", "Expenses", "Savings Goal", "Surplus"]
            values = [income, total_expenses, savings_goal, surplus]
            colors = ["green", "red", "blue", "orange"]
            
            bars = ax1.bar(categories, values, color=colors, alpha=0.7)
            ax1.set_title("Financial Overview", color='white')
            ax1.set_ylabel("Amount (₹)", color='white')
            ax1.tick_params(colors='white')
            
            for bar in bars:
                height = bar.get_height()
                ax1.text(bar.get_x() + bar.get_width()/2., height,
                        f'₹{int(height):,}', ha='center', va='bottom', color='white')
            
            plt.tight_layout()
        
        # Pie chart for expense breakdown
        if expenses and len(expenses) > 0:
            fig_pie, ax2 = plt.subplots(figsize=(8, 8))
            fig_pie.patch.set_alpha(0)
            ax2.patch.set_alpha(0)
            
            labels = list(expenses.keys())
            sizes = list(expenses.values())
            
            # Filter out zero values
            filtered_data = [(l, s) for l, s in zip(labels, sizes) if s > 0]
            if filtered_data:
                labels, sizes = zip(*filtered_data)
                wedges, texts, autotexts = ax2.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
                
                for text in texts:
                    text.set_color('white')
                for text in autotexts:
                    text.set_color('black')
            else:
                ax2.text(0.5, 0.5, 'No expense data', ha='center', va='center', color='white', transform=ax2.transAxes)
            
            plt.tight_layout()
        else:
            # Empty pie chart
            fig_pie, ax2 = plt.subplots(figsize=(8, 8))
            fig_pie.patch.set_alpha(0)
            ax2.patch.set_alpha(0)
            ax2.text(0.5, 0.5, 'No expense data available', ha='center', va='center', 
                    color='white', transform=ax2.transAxes)
            plt.tight_layout()
        
        return fig_bar, fig_pie
    
    def extract_financial_data_from_transactions(
        self,
        transaction_summary: Dict[str, Any],
        profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Extract financial data structure from transaction summary
        
        Args:
            transaction_summary: Transaction data from enhanced_csv_tools
            profile: User profile with income and savings goals
        
        Returns:
            Dict with income, expenses, savings_goal
        """
        # Get income from profile or estimate from transactions
        income = 0
        if profile:
            # Try to get monthly income from profile
            income = profile.get("monthly_income", 0) or profile.get("income", 0)
        
        # If no income in profile, we don't estimate. Let the system know it's missing.
        # This prevents dummy data from appearing in analysis.
        if income == 0:
            # If no income in profile, we don't estimate. Let the system know it's missing.
            income = 0.0
        
        # Get expenses by category
        expenses = {}
        if transaction_summary:
            # Use category breakdown if available
            category_breakdown = transaction_summary.get("category_breakdown", {})
            if isinstance(category_breakdown, dict) and len(category_breakdown) > 0:
                expenses = category_breakdown
            else:
                # Fallback: use monthly spend distributed across top categories
                monthly_spend = transaction_summary.get("monthly_spend", 0)
                if monthly_spend > 0:
                    top_cats = transaction_summary.get("top_categories", [])
                    if top_cats:
                        per_cat = monthly_spend / len(top_cats)
                        expenses = {cat: per_cat for cat in top_cats}
                    else:
                        # If no categories, use "Other" as single category
                        expenses = {"Other": monthly_spend}
        
        # Get savings goal from profile
        savings_goal = 0
        if profile:
            savings_goal = profile.get("savings_goal", 0) or profile.get("budget_goal", 0)
        
        # If no savings goal, set to 20% of income as default
        if savings_goal == 0 and income > 0:
            savings_goal = income * 0.2
        
        return {
            "income": income,
            "expenses": expenses,
            "savings_goal": savings_goal
        }

