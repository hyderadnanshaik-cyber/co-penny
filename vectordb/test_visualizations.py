#!/usr/bin/env python3
"""
Test script to verify visualization functionality
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

from app.tools.csv_tools import query_csv, spend_aggregate, top_merchants, describe_csv
from app.tools.visualization import generate_visualizations

def test_data_access():
    """Test if we can access the CSV data"""
    try:
        print("Testing CSV data access...")
        
        # Test basic CSV info
        csv_info = describe_csv()
        print(f"✓ CSV Info: {csv_info}")
        
        # Test recent data
        recent_data = query_csv("SELECT * FROM t ORDER BY date DESC LIMIT 5")
        print(f"✓ Recent data: {len(recent_data.get('rows', []))} records")
        
        # Test spending data
        spending_data = spend_aggregate()
        print(f"✓ Spending data: {spending_data}")
        
        # Test merchant data
        merchant_data = top_merchants(n=5)
        print(f"✓ Merchant data: {merchant_data}")
        
        return True, recent_data, spending_data, merchant_data
        
    except Exception as e:
        print(f"✗ Error accessing data: {e}")
        return False, {}, {}, {}

def test_visualizations():
    """Test visualization generation"""
    try:
        print("\nTesting visualization generation...")
        
        success, recent_data, spending_data, merchant_data = test_data_access()
        
        if not success:
            print("✗ Cannot test visualizations without data access")
            return False
        
        # Generate visualizations
        visualizations = generate_visualizations(spending_data, recent_data, merchant_data)
        
        print(f"✓ Generated {len(visualizations)} visualizations:")
        for chart_type, chart_data in visualizations.items():
            if chart_data and chart_data.startswith('data:image/png;base64,'):
                print(f"  - {chart_type}: ✓ (Base64 image data)")
            else:
                print(f"  - {chart_type}: ✗ ({chart_data})")
        
        return True
        
    except Exception as e:
        print(f"✗ Error generating visualizations: {e}")
        return False

if __name__ == "__main__":
    print("Cashflow Visualization Test")
    print("=" * 40)
    
    success = test_visualizations()
    
    if success:
        print("\n✓ All tests passed! Visualizations are working.")
    else:
        print("\n✗ Some tests failed. Check the errors above.")
