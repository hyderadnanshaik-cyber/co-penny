import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import seaborn as sns
import pandas as pd
import base64
import io
from typing import Dict, List, Any, Optional
import os
from datetime import datetime, timedelta

# Set style for better looking plots
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")

def create_spending_pie_chart(data: Dict[str, Any]) -> str:
    """Create a pie chart for spending by category"""
    try:
        if not data.get('totals'):
            return ""
        
        # Extract category data
        categories = []
        amounts = []
        for item in data['totals']:
            categories.append(item.get('key', 'Unknown'))
            amounts.append(item.get('spent', 0))
        
        # Create pie chart
        fig, ax = plt.subplots(figsize=(10, 8))
        wedges, texts, autotexts = ax.pie(amounts, labels=categories, autopct='%1.1f%%', startangle=90)
        
        # Improve text appearance
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')
        
        label = ""
        try:
            meta = data.get('meta', {}) if isinstance(data, dict) else {}
            if isinstance(meta, dict) and meta.get('label'):
                label = f" ({meta['label']})"
        except Exception:
            pass
        ax.set_title('Spending by Category' + label, fontsize=16, fontweight='bold', pad=20)
        
        # Convert to base64
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
        img_buffer.seek(0)
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
        plt.close()
        
        return f"data:image/png;base64,{img_base64}"
    except Exception as e:
        return f"Error creating pie chart: {str(e)}"

def create_spending_trend_chart(csv_data: Dict[str, Any]) -> str:
    """Create a line chart showing spending trends over time"""
    try:
        if not csv_data.get('rows'):
            return ""
        
        # Convert to DataFrame
        df = pd.DataFrame(csv_data['rows'])
        if 'date' not in df.columns:
            return ""
        
        # Convert date column
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        # Group by month and sum expenses
        df['month'] = df['date'].dt.to_period('M')
        monthly_spending = df.groupby('month')['monthly_expense_total'].sum()
        
        # Create line chart
        fig, ax = plt.subplots(figsize=(12, 6))
        monthly_spending.plot(kind='line', marker='o', linewidth=2, markersize=6, ax=ax)
        
        label = ""
        try:
            meta = csv_data.get('meta', {}) if isinstance(csv_data, dict) else {}
            if isinstance(meta, dict) and meta.get('label'):
                label = f" ({meta['label']})"
        except Exception:
            pass
        ax.set_title('Monthly Spending Trend' + label, fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('Month', fontsize=12)
        ax.set_ylabel('Total Spending (INR)', fontsize=12)
        ax.grid(True, alpha=0.3)
        
        # Rotate x-axis labels
        plt.xticks(rotation=45)
        
        # Convert to base64
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
        img_buffer.seek(0)
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
        plt.close()
        
        return f"data:image/png;base64,{img_base64}"
    except Exception as e:
        return f"Error creating trend chart: {str(e)}"

def create_income_trend_chart(csv_data: Dict[str, Any]) -> str:
    """Create a line chart showing salary/income over time"""
    try:
        if not csv_data.get('rows'):
            return ""
        df = pd.DataFrame(csv_data['rows'])
        if 'date' not in df.columns or 'monthly_income' not in df.columns:
            return ""
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        df['month'] = df['date'].dt.to_period('M')
        monthly_income = df.groupby('month')['monthly_income'].sum()
        fig, ax = plt.subplots(figsize=(12, 6))
        monthly_income.plot(kind='line', marker='o', linewidth=2, markersize=6, ax=ax, color='#2E86AB')
        label = ""
        try:
            meta = csv_data.get('meta', {}) if isinstance(csv_data, dict) else {}
            if isinstance(meta, dict) and meta.get('label'):
                label = f" ({meta['label']})"
        except Exception:
            pass
        ax.set_title('Monthly Salary Trend' + label, fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('Month', fontsize=12)
        ax.set_ylabel('Total Salary (INR)', fontsize=12)
        ax.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
        img_buffer.seek(0)
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
        plt.close()
        return f"data:image/png;base64,{img_base64}"
    except Exception as e:
        return f"Error creating income trend chart: {str(e)}"

def create_category_bar_chart(data: Dict[str, Any]) -> str:
    """Create a bar chart for spending by category"""
    try:
        if not data.get('totals'):
            return ""
        
        # Extract category data
        categories = []
        amounts = []
        for item in data['totals']:
            categories.append(item.get('key', 'Unknown'))
            amounts.append(item.get('spent', 0))
        
        # Create bar chart
        fig, ax = plt.subplots(figsize=(12, 8))
        bars = ax.bar(categories, amounts, color=sns.color_palette("husl", len(categories)))
        
        # Add value labels on bars
        for bar, amount in zip(bars, amounts):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                   f'₹{amount:,.0f}', ha='center', va='bottom', fontweight='bold')
        
        label = ""
        try:
            meta = data.get('meta', {}) if isinstance(data, dict) else {}
            if isinstance(meta, dict) and meta.get('label'):
                label = f" ({meta['label']})"
        except Exception:
            pass
        ax.set_title('Spending by Category' + label, fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('Category', fontsize=12)
        ax.set_ylabel('Amount Spent (INR)', fontsize=12)
        
        # Rotate x-axis labels
        plt.xticks(rotation=45, ha='right')
        
        # Convert to base64
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
        img_buffer.seek(0)
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
        plt.close()
        
        return f"data:image/png;base64,{img_base64}"
    except Exception as e:
        return f"Error creating bar chart: {str(e)}"

def create_merchant_chart(merchant_data: Dict[str, Any]) -> str:
    """Create a horizontal bar chart for top merchants"""
    try:
        if not merchant_data.get('items'):
            return ""
        
        # Extract merchant data
        merchants = []
        amounts = []
        for item in merchant_data['items'][:10]:  # Top 10 merchants
            merchants.append(item.get('merchant', 'Unknown'))
            amounts.append(item.get('spent', 0))
        
        # Create horizontal bar chart
        fig, ax = plt.subplots(figsize=(12, 8))
        bars = ax.barh(merchants, amounts, color=sns.color_palette("viridis", len(merchants)))
        
        # Add value labels
        for i, (bar, amount) in enumerate(zip(bars, amounts)):
            width = bar.get_width()
            ax.text(width + width*0.01, bar.get_y() + bar.get_height()/2,
                   f'₹{amount:,.0f}', ha='left', va='center', fontweight='bold')
        
        label = ""
        try:
            meta = merchant_data.get('meta', {}) if isinstance(merchant_data, dict) else {}
            if isinstance(meta, dict) and meta.get('label'):
                label = f" ({meta['label']})"
        except Exception:
            pass
        ax.set_title('Top Merchants by Spending' + label, fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('Amount Spent (INR)', fontsize=12)
        ax.set_ylabel('Merchant', fontsize=12)
        
        # Convert to base64
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
        img_buffer.seek(0)
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
        plt.close()
        
        return f"data:image/png;base64,{img_base64}"
    except Exception as e:
        return f"Error creating merchant chart: {str(e)}"

def generate_visualizations(spending_data: Dict[str, Any], csv_data: Dict[str, Any], merchant_data: Dict[str, Any]) -> Dict[str, str]:
    """Generate all relevant visualizations based on available data"""
    visualizations = {}
    
    try:
        # Generate pie chart
        pie_chart = create_spending_pie_chart(spending_data)
        if pie_chart and not pie_chart.startswith("Error"):
            visualizations['pie_chart'] = pie_chart
        
        # Generate bar chart
        bar_chart = create_category_bar_chart(spending_data)
        if bar_chart and not bar_chart.startswith("Error"):
            visualizations['bar_chart'] = bar_chart
        
        # Generate trend chart
        trend_chart = create_spending_trend_chart(csv_data)
        if trend_chart and not trend_chart.startswith("Error"):
            visualizations['trend_chart'] = trend_chart
        
        # Generate merchant chart
        merchant_chart = create_merchant_chart(merchant_data)
        if merchant_chart and not merchant_chart.startswith("Error"):
            visualizations['merchant_chart'] = merchant_chart
            
    except Exception as e:
        visualizations['error'] = f"Error generating visualizations: {str(e)}"
    
    return visualizations

def create_monthly_spending_chart(csv_data: Dict[str, Any]) -> str:
    """Create a monthly spending chart"""
    try:
        if not csv_data.get('rows'):
            return ""
        
        # Process data for monthly spending
        monthly_data = {}
        for row in csv_data['rows']:
            date_str = row.get('date', '')
            if date_str:
                month = date_str[:7]  # YYYY-MM format
                amount = float(row.get('monthly_expense_total', 0))
                monthly_data[month] = monthly_data.get(month, 0) + amount
        
        if not monthly_data:
            return ""
        
        # Sort by month
        sorted_months = sorted(monthly_data.keys())
        amounts = [monthly_data[month] for month in sorted_months]
        
        # Create chart
        fig, ax = plt.subplots(figsize=(12, 6))
        bars = ax.bar(sorted_months, amounts, color='skyblue', edgecolor='navy', alpha=0.7)
        
        # Add value labels
        for bar, amount in zip(bars, amounts):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                   f'₹{amount:,.0f}', ha='center', va='bottom', fontweight='bold')
        
        label = ""
        try:
            meta = csv_data.get('meta', {}) if isinstance(csv_data, dict) else {}
            if isinstance(meta, dict) and meta.get('label'):
                label = f" ({meta['label']})"
        except Exception:
            pass
        ax.set_title('Monthly Spending Overview' + label, fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('Month', fontsize=12)
        ax.set_ylabel('Amount Spent (INR)', fontsize=12)
        ax.tick_params(axis='x', rotation=45)
        
        # Convert to base64
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
        img_buffer.seek(0)
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
        plt.close()
        
        return f"data:image/png;base64,{img_base64}"
    except Exception as e:
        return f"Error creating monthly chart: {str(e)}"

def create_daily_spending_chart(csv_data: Dict[str, Any]) -> str:
    """Create a daily spending chart for the last 30 days"""
    try:
        if not csv_data.get('rows'):
            return ""
        
        # Process data for daily spending (last 30 days)
        daily_data = {}
        for row in csv_data['rows']:
            date_str = row.get('date', '')
            if date_str:
                amount = float(row.get('monthly_expense_total', 0))
                daily_data[date_str] = daily_data.get(date_str, 0) + amount
        
        if not daily_data:
            return ""
        
        # Sort by date and take last 30 days
        sorted_dates = sorted(daily_data.keys())[-30:]
        amounts = [daily_data[date] for date in sorted_dates]
        
        # Create chart
        fig, ax = plt.subplots(figsize=(14, 6))
        ax.plot(sorted_dates, amounts, marker='o', linewidth=2, markersize=4, color='green')
        ax.fill_between(sorted_dates, amounts, alpha=0.3, color='green')
        
        label = ""
        try:
            meta = csv_data.get('meta', {}) if isinstance(csv_data, dict) else {}
            if isinstance(meta, dict) and meta.get('label'):
                label = f" ({meta['label']})"
        except Exception:
            pass
        ax.set_title('Daily Spending Trend (Last 30 Days)' + label, fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('Amount Spent (INR)', fontsize=12)
        ax.tick_params(axis='x', rotation=45)
        
        # Convert to base64
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
        img_buffer.seek(0)
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
        plt.close()
        
        return f"data:image/png;base64,{img_base64}"
    except Exception as e:
        return f"Error creating daily chart: {str(e)}"

def create_amount_distribution_chart(csv_data: Dict[str, Any]) -> str:
    """Create a histogram of transaction amounts"""
    try:
        if not csv_data.get('rows'):
            return ""
        
        # Extract amounts
        amounts = []
        for row in csv_data['rows']:
            amount = float(row.get('monthly_expense_total', 0))
            if amount > 0:
                amounts.append(amount)
        
        if not amounts:
            return ""
        
        # Create histogram
        fig, ax = plt.subplots(figsize=(10, 6))
        n, bins, patches = ax.hist(amounts, bins=20, color='lightcoral', edgecolor='black', alpha=0.7)
        
        # Color bars by height
        for i, (bar, count) in enumerate(zip(patches, n)):
            bar.set_facecolor(plt.cm.viridis(count / max(n)))
        
        label = ""
        try:
            meta = csv_data.get('meta', {}) if isinstance(csv_data, dict) else {}
            if isinstance(meta, dict) and meta.get('label'):
                label = f" ({meta['label']})"
        except Exception:
            pass
        ax.set_title('Transaction Amount Distribution' + label, fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('Amount (INR)', fontsize=12)
        ax.set_ylabel('Frequency', fontsize=12)
        
        # Add statistics
        mean_amount = sum(amounts) / len(amounts)
        ax.axvline(mean_amount, color='red', linestyle='--', linewidth=2, label=f'Mean: ₹{mean_amount:,.0f}')
        ax.legend()
        
        # Convert to base64
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
        img_buffer.seek(0)
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
        plt.close()
        
        return f"data:image/png;base64,{img_base64}"
    except Exception as e:
        return f"Error creating amount distribution chart: {str(e)}"

def create_category_comparison_chart(spending_data: Dict[str, Any]) -> str:
    """Create a comparison chart between categories"""
    try:
        if not spending_data.get('totals'):
            return ""
        
        # Extract data
        categories = []
        amounts = []
        for item in spending_data['totals']:
            categories.append(item.get('key', 'Unknown'))
            amounts.append(item.get('spent', 0))
        
        if not categories:
            return ""
        
        # Create horizontal bar chart for better comparison
        fig, ax = plt.subplots(figsize=(10, 8))
        y_pos = range(len(categories))
        bars = ax.barh(y_pos, amounts, color='lightblue', edgecolor='navy')
        
        # Add value labels
        for i, (bar, amount) in enumerate(zip(bars, amounts)):
            width = bar.get_width()
            ax.text(width + width*0.01, bar.get_y() + bar.get_height()/2,
                   f'₹{amount:,.0f}', ha='left', va='center', fontweight='bold')
        
        ax.set_yticks(y_pos)
        ax.set_yticklabels(categories)
        ax.set_xlabel('Amount Spent (INR)', fontsize=12)
        ax.set_title('Category Spending Comparison', fontsize=16, fontweight='bold', pad=20)
        
        # Convert to base64
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
        img_buffer.seek(0)
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
        plt.close()
        
        return f"data:image/png;base64,{img_base64}"
    except Exception as e:
        return f"Error creating comparison chart: {str(e)}"

def generate_dynamic_visualizations(user_message: str, spending_data: Dict[str, Any], recent_data: Dict[str, Any], merchants_data: Dict[str, Any]) -> Dict[str, str]:
    """Generate visualizations based on user's specific request"""
    visualizations = {}
    message_lower = user_message.lower()
    
    try:
        # Analyze user request and generate appropriate charts
        if any(word in message_lower for word in ['pie', 'pie chart', 'category', 'breakdown', 'distribution', 'expenditure']):
            pie_chart = create_spending_pie_chart(spending_data)
            if pie_chart and not pie_chart.startswith("Error"):
                visualizations['spending_by_category'] = pie_chart
        
        if any(word in message_lower for word in ['bar', 'bar chart', 'merchant', 'merchants', 'top', 'highest']):
            merchants_chart = create_merchant_chart(merchants_data)
            if merchants_chart and not merchants_chart.startswith("Error"):
                visualizations['top_merchants'] = merchants_chart
        
        if any(word in message_lower for word in ['line', 'line chart', 'trend', 'trends', 'over time', 'timeline']):
            trends_chart = create_spending_trend_chart(recent_data)
            if trends_chart and not trends_chart.startswith("Error"):
                visualizations['spending_trends'] = trends_chart

        if any(word in message_lower for word in ['salary', 'income', 'pay']):
            income_chart = create_income_trend_chart(recent_data)
            if income_chart and not income_chart.startswith("Error"):
                visualizations['salary_trend'] = income_chart
        
        if any(word in message_lower for word in ['monthly', 'month', 'monthly spending', 'monthly analysis']):
            monthly_chart = create_monthly_spending_chart(recent_data)
            if monthly_chart and not monthly_chart.startswith("Error"):
                visualizations['monthly_spending'] = monthly_chart
        
        if any(word in message_lower for word in ['daily', 'day', 'daily spending', 'daily analysis']):
            daily_chart = create_daily_spending_chart(recent_data)
            if daily_chart and not daily_chart.startswith("Error"):
                visualizations['daily_spending'] = daily_chart
        
        if any(word in message_lower for word in ['amount', 'amounts', 'transaction amounts', 'amount distribution', 'histogram']):
            amounts_chart = create_amount_distribution_chart(recent_data)
            if amounts_chart and not amounts_chart.startswith("Error"):
                visualizations['amount_distribution'] = amounts_chart
        
        if any(word in message_lower for word in ['comparison', 'compare', 'vs', 'versus', 'expenditure']):
            comparison_chart = create_category_comparison_chart(spending_data)
            if comparison_chart and not comparison_chart.startswith("Error"):
                visualizations['category_comparison'] = comparison_chart
        
        # If no specific chart type mentioned, create a comprehensive dashboard
        if not visualizations and any(word in message_lower for word in ['chart', 'graph', 'plot', 'visualize', 'show me', 'display']):
            # Create default set of charts
            pie_chart = create_spending_pie_chart(spending_data)
            if pie_chart and not pie_chart.startswith("Error"):
                visualizations['spending_by_category'] = pie_chart
            
            merchants_chart = create_merchant_chart(merchants_data)
            if merchants_chart and not merchants_chart.startswith("Error"):
                visualizations['top_merchants'] = merchants_chart
            
            trends_chart = create_spending_trend_chart(recent_data)
            if trends_chart and not trends_chart.startswith("Error"):
                visualizations['spending_trends'] = trends_chart
                
    except Exception as e:
        print(f"Error generating dynamic visualizations: {e}")
    
    return visualizations

def create_historical_yearly_trend_chart(yearly_data: List[Dict[str, Any]], title: str = "Yearly Spending Trend") -> str:
    """Create a yearly trend chart for historical analysis"""
    try:
        if not yearly_data:
            return ""
        
        years = [str(item['year']) for item in yearly_data]
        amounts = [item['monthly_expense_total'] for item in yearly_data]
        
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(years, amounts, marker='o', linewidth=2, markersize=6, color='#2E86AB')
        ax.fill_between(years, amounts, alpha=0.3, color='#2E86AB')
        
        ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('Year', fontsize=12)
        ax.set_ylabel('Total Spending (INR)', fontsize=12)
        ax.grid(True, alpha=0.3)
        
        # Add value labels on points
        for i, (year, amount) in enumerate(zip(years, amounts)):
            ax.annotate(f'₹{amount:,.0f}', (year, amount), 
                       textcoords="offset points", xytext=(0,10), ha='center')
        
        # Convert to base64
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
        img_buffer.seek(0)
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
        plt.close()
        
        return f"data:image/png;base64,{img_base64}"
    except Exception as e:
        return f"Error creating yearly trend chart: {str(e)}"

def create_historical_monthly_breakdown_chart(monthly_data: List[Dict[str, Any]], title: str = "Monthly Spending Breakdown") -> str:
    """Create a monthly breakdown chart for historical analysis"""
    try:
        if not monthly_data:
            return ""
        
        months = [item['month_name'] for item in monthly_data]
        amounts = [item['monthly_expense_total'] for item in monthly_data]
        
        fig, ax = plt.subplots(figsize=(12, 6))
        bars = ax.bar(months, amounts, color='#A23B72', alpha=0.8)
        
        # Add value labels on bars
        for bar, amount in zip(bars, amounts):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                   f'₹{amount:,.0f}', ha='center', va='bottom', fontweight='bold')
        
        ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('Month', fontsize=12)
        ax.set_ylabel('Amount Spent (INR)', fontsize=12)
        ax.tick_params(axis='x', rotation=45)
        
        # Convert to base64
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
        img_buffer.seek(0)
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
        plt.close()
        
        return f"data:image/png;base64,{img_base64}"
    except Exception as e:
        return f"Error creating monthly breakdown chart: {str(e)}"

def create_historical_category_breakdown_chart(categories: List[Dict[str, Any]], title: str = "Spending by Category") -> str:
    """Create a category breakdown chart for historical analysis"""
    try:
        if not categories:
            return ""
        
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
        
        ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('Amount Spent (INR)', fontsize=12)
        ax.set_ylabel('Category', fontsize=12)
        
        # Convert to base64
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
        img_buffer.seek(0)
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
        plt.close()
        
        return f"data:image/png;base64,{img_base64}"
    except Exception as e:
        return f"Error creating category breakdown chart: {str(e)}"

def create_historical_top_merchants_chart(merchants: List[Dict[str, Any]], title: str = "Top Merchants by Spending") -> str:
    """Create a top merchants chart for historical analysis"""
    try:
        if not merchants:
            return ""
        
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
        
        ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('Amount Spent (INR)', fontsize=12)
        ax.set_ylabel('Merchant', fontsize=12)
        
        # Convert to base64
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
        img_buffer.seek(0)
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
        plt.close()
        
        return f"data:image/png;base64,{img_base64}"
    except Exception as e:
        return f"Error creating top merchants chart: {str(e)}"

def generate_historical_visualizations(historical_data: Dict[str, Any], message: str = "") -> Dict[str, str]:
    """Generate visualizations for historical data analysis"""
    visualizations = {}
    
    try:
        if not historical_data.get('data_available', False):
            return {}
        
        # Generate yearly trend chart
        if 'yearly_breakdown' in historical_data and historical_data['yearly_breakdown']:
            yearly_chart = create_historical_yearly_trend_chart(historical_data['yearly_breakdown'])
            if yearly_chart and not yearly_chart.startswith("Error"):
                visualizations['yearly_trend'] = yearly_chart
        
        # Generate monthly breakdown chart
        if 'monthly_breakdown' in historical_data and historical_data['monthly_breakdown']:
            monthly_chart = create_historical_monthly_breakdown_chart(historical_data['monthly_breakdown'])
            if monthly_chart and not monthly_chart.startswith("Error"):
                visualizations['monthly_breakdown'] = monthly_chart
        
        # Generate category breakdown chart
        if 'categories' in historical_data and historical_data['categories']:
            category_chart = create_historical_category_breakdown_chart(historical_data['categories'])
            if category_chart and not category_chart.startswith("Error"):
                visualizations['category_breakdown'] = category_chart
        
        # Generate top merchants chart
        if 'top_merchants' in historical_data and historical_data['top_merchants']:
            merchants_chart = create_historical_top_merchants_chart(historical_data['top_merchants'])
            if merchants_chart and not merchants_chart.startswith("Error"):
                visualizations['top_merchants'] = merchants_chart
                
    except Exception as e:
        print(f"Error generating historical visualizations: {e}")
    
    return visualizations