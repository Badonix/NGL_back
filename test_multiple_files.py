#!/usr/bin/env python3

import requests
import io

def test_multiple_files():
    print("Testing multiple file upload...")
    
    # Create sample file contents
    file1_content = """
    Financial Statement 2023 - Income Statement
    Revenue: $1,000,000
    COGS: $600,000
    Gross Profit: $400,000
    Operating Expenses: $200,000
    Net Income: $200,000
    """
    
    file2_content = """
    Balance Sheet 2023
    Cash: $50,000
    Accounts Receivable: $150,000
    Inventory: $100,000
    Total Assets: $500,000
    Total Liabilities: $200,000
    Shareholders Equity: $300,000
    """
    
    # Create file-like objects
    files = [
        ('files', ('income_statement.txt', io.BytesIO(file1_content.encode('utf-8')), 'text/plain')),
        ('files', ('balance_sheet.txt', io.BytesIO(file2_content.encode('utf-8')), 'text/plain'))
    ]
    
    try:
        response = requests.post(
            "http://localhost:5000/evaluate",
            files=files,
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ SUCCESS!")
            print(f"File Count: {data.get('file_count', 'Not specified')}")
            print(f"Processed Files: {data.get('processed_files', 'Not specified')}")
            print(f"Total Length: {data.get('length', 'Not specified')}")
            print(f"Filename: {data.get('filename', 'Not specified')}")
            
            if data.get('success'):
                print("✅ Financial analysis completed successfully!")
            else:
                print("⚠️ Financial analysis had issues")
                
        else:
            print("❌ FAILED!")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    test_multiple_files()
