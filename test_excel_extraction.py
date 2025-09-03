#!/usr/bin/env python3

import pandas as pd
import os
from services.text_extractor import TextExtractor

def create_test_excel():
    """Create a test Excel file with financial data"""
    
    # Create sample financial data
    income_statement_data = {
        'Financial Item': [
            'Revenue',
            'Cost of Goods Sold', 
            'Gross Profit',
            'Operating Expenses',
            'Operating Income',
            'Interest Expense',
            'Net Income'
        ],
        '2022': [1000000, 600000, 400000, 200000, 200000, 20000, 180000],
        '2023': [1200000, 720000, 480000, 240000, 240000, 25000, 215000]
    }
    
    balance_sheet_data = {
        'Financial Item': [
            'Cash and Cash Equivalents',
            'Accounts Receivable',
            'Inventory', 
            'Total Current Assets',
            'Property, Plant & Equipment',
            'Total Assets',
            'Accounts Payable',
            'Short-term Debt',
            'Total Current Liabilities',
            'Long-term Debt',
            'Total Shareholders Equity'
        ],
        '2022': [50000, 150000, 200000, 400000, 300000, 700000, 100000, 50000, 150000, 200000, 350000],
        '2023': [75000, 180000, 240000, 495000, 350000, 845000, 120000, 60000, 180000, 250000, 415000]
    }
    
    # Create Excel file with multiple sheets
    test_file = 'test_financial_data.xlsx'
    
    with pd.ExcelWriter(test_file, engine='openpyxl') as writer:
        pd.DataFrame(income_statement_data).to_excel(writer, sheet_name='Income Statement', index=False)
        pd.DataFrame(balance_sheet_data).to_excel(writer, sheet_name='Balance Sheet', index=False)
    
    return test_file

def test_excel_extraction():
    """Test the Excel extraction functionality"""
    
    print("Creating test Excel file...")
    test_file = create_test_excel()
    
    try:
        print(f"Testing extraction from: {test_file}")
        
        # Test the extraction
        extracted_text = TextExtractor.extract_text_from_file(test_file)
        
        print("✅ SUCCESS! Excel extraction completed.")
        print(f"Extracted text length: {len(extracted_text)} characters")
        print("\n--- EXTRACTED CONTENT (first 1000 chars) ---")
        print(extracted_text[:1000])
        print("...")
        
        # Verify content contains expected elements
        if "Income Statement" in extracted_text:
            print("✅ Income Statement sheet found")
        else:
            print("❌ Income Statement sheet missing")
            
        if "Balance Sheet" in extracted_text:
            print("✅ Balance Sheet sheet found")
        else:
            print("❌ Balance Sheet sheet missing")
            
        if "Revenue" in extracted_text and "1000000" in extracted_text:
            print("✅ Financial data found")
        else:
            print("❌ Financial data missing")
            
    except Exception as e:
        print(f"❌ FAILED: {e}")
        
    finally:
        # Cleanup
        if os.path.exists(test_file):
            os.remove(test_file)
            print(f"Cleaned up test file: {test_file}")

if __name__ == "__main__":
    print("Testing Excel file extraction...\n")
    test_excel_extraction()
