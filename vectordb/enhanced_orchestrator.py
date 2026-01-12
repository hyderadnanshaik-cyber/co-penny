import json
import os
from typing import List, Dict, Any, Optional
from llm.llm_client import LLMClient
from llm.prompts import system_advisor
from llm.json_guard import validate_json_response
from app.tools.csv_tools import query_csv, spend_aggregate, top_merchants, describe_csv
from app.tools.enhanced_csv_tools import (
    extract_year_data, extract_year_range_data, extract_month_data, 
    extract_date_range_data, parse_historical_query, get_available_years,
    format_currency, format_date
)
from app.tools.visualization import generate_visualizations, generate_dynamic_visualizations

class HistoricalAnalysisOrchestrator:
    def __init__(self):
        self.llm_client = LLMClient()
        self.artifacts_dir = os.path.join(os.path.dirname(__file__), "artifacts")
        self._ensure_artifacts_dir()
        
    def _ensure_artifacts_dir(self):
        """Create artifacts directory if it doesn't exist"""
        if not os.path.exists(self.artifacts_dir):
            os.makedirs(self.artifacts_dir)
    
    def _is_historical_query(self, message: str) -> bool:
        """Check if the message is asking for historical analysis"""
        historical_keywords = [
            '2018', '2019', '2020', '2021', '2022', '2023', '2024',
            'historical', 'history', 'past', 'previous', 'earlier',
            'year', 'years', 'month', 'months', 'january', 'february',
            'march', 'april', 'may', 'june', 'july', 'august',
            'september', 'october', 'november', 'december',
            'expenditure analysis', 'spending analysis', 'expense analysis',
            'from', 'to', 'between', 'range', 'period'
        ]
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in historical_keywords)
    
    def _extract_historical_data(self, message: str) -> Dict[str, Any]:
        """Extract historical data based on the query"""
        try:
            parsed_query = parse_historical_query(message)
            
            if parsed_query['query_type'] == 'year':
                years = parsed_query['years']
                if len(years) == 1:
                    return extract_year_data(years[0])
                elif len(years) > 1:
                    return extract_year_range_data(min(years), max(years))
                else:
                    # No specific year mentioned, get available years
                    available_years = get_available_years()
                    if available_years:
                        return extract_year_data(available_years[-1])  # Most recent year
                    return {"error": "No data available", "data_available": False}
            
            elif parsed_query['query_type'] == 'month':
                months = parsed_query['months']
                years = parsed_query['years']
                if years:
                    year = years[0]
                else:
                    available_years = get_available_years()
                    year = available_years[-1] if available_years else 2023
                
                if months:
                    return extract_month_data(year, months[0])
                else:
                    return extract_year_data(year)
            
            elif parsed_query['query_type'] == 'date_range':
                start_date, end_date = parsed_query['date_range']
                return extract_date_range_data(start_date, end_date)
            
            else:
                # General historical query - get most recent year
                available_years = get_available_years()
                if available_years:
                    return extract_year_data(available_years[-1])
                return {"error": "No data available", "data_available": False}
                
        except Exception as e:
            return {"error": str(e), "data_available": False}
    
    def _generate_historical_charts(self, historical_data: Dict[str, Any], message: str) -> Dict[str, str]:
        """Generate charts for historical data"""
        try:
            if not historical_data.get('data_available', False):
                return {}
            
            charts = {}
            
            # Generate time series chart for yearly data
            if 'yearly_breakdown' in historical_data and historical_data['yearly_breakdown']:
                charts['yearly_trend'] = self._create_yearly_trend_chart(historical_data['yearly_breakdown'])
            
            # Generate monthly breakdown chart
            if 'monthly_breakdown' in historical_data and historical_data['monthly_breakdown']:
                charts['monthly_breakdown'] = self._create_monthly_breakdown_chart(historical_data['monthly_breakdown'])
            
            # Generate category breakdown chart
            if 'categories' in historical_data and historical_data['categories']:
                charts['category_breakdown'] = self._create_category_breakdown_chart(historical_data['categories'])
            
            # Generate top merchants chart
            if 'top_merchants' in historical_data and historical_data['top_merchants']:
                charts['top_merchants'] = self._create_top_merchants_chart(historical_data['top_merchants'])
            
            return charts
            
        except Exception as e:
            print(f"Error generating historical charts: {e}")
            return {}
    
    def _create_yearly_trend_chart(self, yearly_data: List[Dict]) -> str:
        """Create a yearly trend chart"""
        try:
            import matplotlib.pyplot as plt
            import matplotlib
            matplotlib.use('Agg')
            import base64
            import io
            
            years = [str(item['year']) for item in yearly_data]
            amounts = [item['monthly_expense_total'] for item in yearly_data]
            
            fig, ax = plt.subplots(figsize=(12, 6))
            ax.plot(years, amounts, marker='o', linewidth=2, markersize=6, color='#2E86AB')
            ax.fill_between(years, amounts, alpha=0.3, color='#2E86AB')
            
            ax.set_title('Yearly Spending Trend', fontsize=16, fontweight='bold', pad=20)
            ax.set_xlabel('Year', fontsize=12)
            ax.set_ylabel('Total Spending (INR)', fontsize=12)
            ax.grid(True, alpha=0.3)
            
            # Add value labels on points
            for i, (year, amount) in enumerate(zip(years, amounts)):
                ax.annotate(f'₹{amount:,.0f}', (year, amount), 
                           textcoords="offset points", xytext=(0,10), ha='center')
            
            # Save to artifacts directory
            chart_path = os.path.join(self.artifacts_dir, f"yearly_trend_{years[0]}_{years[-1]}.png")
            plt.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            return f"file://{chart_path}"
            
        except Exception as e:
            return f"Error creating yearly trend chart: {str(e)}"
    
    def _create_monthly_breakdown_chart(self, monthly_data: List[Dict]) -> str:
        """Create a monthly breakdown chart"""
        try:
            import matplotlib.pyplot as plt
            import matplotlib
            matplotlib.use('Agg')
            import base64
            import io
            
            months = [item['month_name'] for item in monthly_data]
            amounts = [item['monthly_expense_total'] for item in monthly_data]
            
            fig, ax = plt.subplots(figsize=(12, 6))
            bars = ax.bar(months, amounts, color='#A23B72', alpha=0.8)
            
            # Add value labels on bars
            for bar, amount in zip(bars, amounts):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                       f'₹{amount:,.0f}', ha='center', va='bottom', fontweight='bold')
            
            ax.set_title('Monthly Spending Breakdown', fontsize=16, fontweight='bold', pad=20)
            ax.set_xlabel('Month', fontsize=12)
            ax.set_ylabel('Amount Spent (INR)', fontsize=12)
            ax.tick_params(axis='x', rotation=45)
            
            # Save to artifacts directory
            chart_path = os.path.join(self.artifacts_dir, "monthly_breakdown.png")
            plt.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            return f"file://{chart_path}"
            
        except Exception as e:
            return f"Error creating monthly breakdown chart: {str(e)}"
    
    def _create_category_breakdown_chart(self, categories: List[Dict]) -> str:
        """Create a category breakdown chart"""
        try:
            import matplotlib.pyplot as plt
            import matplotlib
            matplotlib.use('Agg')
            import base64
            import io
            
            # Take top 10 categories
            top_categories = categories[:10]
            cat_names = [item['category'] for item in top_categories]
            amounts = [item['monthly_expense_total'] for item in top_categories]
            
            fig, ax = plt.subplots(figsize=(12, 8))
            bars = ax.barh(cat_names, amounts, color='#F18F01', alpha=0.8)
            
            # Add value labels
            for i, (bar, amount) in enumerate(zip(bars, amounts)):
                width = bar.get_width()
                ax.text(width + width*0.01, bar.get_y() + bar.get_height()/2,
                       f'₹{amount:,.0f}', ha='left', va='center', fontweight='bold')
            
            ax.set_title('Spending by Category', fontsize=16, fontweight='bold', pad=20)
            ax.set_xlabel('Amount Spent (INR)', fontsize=12)
            ax.set_ylabel('Category', fontsize=12)
            
            # Save to artifacts directory
            chart_path = os.path.join(self.artifacts_dir, "category_breakdown.png")
            plt.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            return f"file://{chart_path}"
            
        except Exception as e:
            return f"Error creating category breakdown chart: {str(e)}"
    
    def _create_top_merchants_chart(self, merchants: List[Dict]) -> str:
        """Create a top merchants chart"""
        try:
            import matplotlib.pyplot as plt
            import matplotlib
            matplotlib.use('Agg')
            import base64
            import io
            
            # Take top 10 merchants
            top_merchants = merchants[:10]
            merchant_names = [item['merchant'] for item in top_merchants]
            amounts = [item['monthly_expense_total'] for item in top_merchants]
            
            fig, ax = plt.subplots(figsize=(12, 8))
            bars = ax.barh(merchant_names, amounts, color='#C73E1D', alpha=0.8)
            
            # Add value labels
            for i, (bar, amount) in enumerate(zip(bars, amounts)):
                width = bar.get_width()
                ax.text(width + width*0.01, bar.get_y() + bar.get_height()/2,
                       f'₹{amount:,.0f}', ha='left', va='center', fontweight='bold')
            
            ax.set_title('Top Merchants by Spending', fontsize=16, fontweight='bold', pad=20)
            ax.set_xlabel('Amount Spent (INR)', fontsize=12)
            ax.set_ylabel('Merchant', fontsize=12)
            
            # Save to artifacts directory
            chart_path = os.path.join(self.artifacts_dir, "top_merchants.png")
            plt.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            return f"file://{chart_path}"
            
        except Exception as e:
            return f"Error creating top merchants chart: {str(e)}"
    
    def _format_historical_summary(self, historical_data: Dict[str, Any]) -> str:
        """Format a concise summary of historical data"""
        if not historical_data.get('data_available', False):
            return "No data available for the requested period."
        
        summary_parts = []
        
        # Basic stats
        if 'year' in historical_data:
            year = historical_data['year']
            total_spent = historical_data.get('total_spent', 0)
            total_transactions = historical_data.get('total_transactions', 0)
            summary_parts.append(f"**{year} Analysis:**")
            summary_parts.append(f"• Total spent: {format_currency(total_spent)}")
            summary_parts.append(f"• Transactions: {total_transactions:,}")
        
        elif 'start_year' in historical_data and 'end_year' in historical_data:
            start_year = historical_data['start_year']
            end_year = historical_data['end_year']
            total_spent = historical_data.get('total_spent', 0)
            total_transactions = historical_data.get('total_transactions', 0)
            summary_parts.append(f"**{start_year}-{end_year} Analysis:**")
            summary_parts.append(f"• Total spent: {format_currency(total_spent)}")
            summary_parts.append(f"• Transactions: {total_transactions:,}")
        
        # Top categories
        if 'categories' in historical_data and historical_data['categories']:
            top_categories = historical_data['categories'][:5]
            summary_parts.append(f"• **Top Categories:**")
            for cat in top_categories:
                summary_parts.append(f"  - {cat['category']}: {format_currency(cat['monthly_expense_total'])}")
        
        # Monthly breakdown if available
        if 'monthly_breakdown' in historical_data and historical_data['monthly_breakdown']:
            summary_parts.append(f"• **Monthly Breakdown:**")
            for month in historical_data['monthly_breakdown'][:6]:  # Show top 6 months
                summary_parts.append(f"  - {month['month_name']}: {format_currency(month['monthly_expense_total'])}")
        
        return "\n".join(summary_parts)
    
    def process_historical_query(self, message: str, context: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """Process a historical analysis query"""
        try:
            # Extract historical data
            historical_data = self._extract_historical_data(message)
            
            if not historical_data.get('data_available', False):
                return {
                    "answer": "I don't have data available for the requested period. Please check the available years or try a different time range.",
                    "status": "error",
                    "type": "text"
                }
            
            # Generate charts
            charts = self._generate_historical_charts(historical_data, message)
            
            # Format summary
            summary = self._format_historical_summary(historical_data)
            
            # Create LLM prompt with data context
            data_context = f"""
HISTORICAL DATA ANALYSIS:
{summary}

CHARTS GENERATED:
{', '.join(charts.keys()) if charts else 'No charts available'}

User Question: {message}

Instructions:
- Provide a concise analysis based on the computed data above
- Reference specific numbers and trends from the data
- Mention the charts that were generated
- Be direct and data-driven
- Use Indian Rupee formatting (₹) with commas
- Don't make up numbers - only use what's computed above
"""
            
            # Get LLM response
            response = self.llm_client.complete(data_context)
            
            # Prepare response
            response_data = {
                "answer": response,
                "status": "success",
                "type": "historical_analysis",
                "data": historical_data,
                "charts": charts
            }
            
            return response_data
            
        except Exception as e:
            return {
                "answer": f"I encountered an error while analyzing historical data: {str(e)}",
                "status": "error",
                "type": "error"
            }

# Create global instance
historical_orchestrator = HistoricalAnalysisOrchestrator()

def process_historical_query(message: str, context: List[Dict[str, str]] = None) -> Dict[str, Any]:
    """Main function for processing historical queries"""
    return historical_orchestrator.process_historical_query(message, context)
