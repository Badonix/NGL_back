#!/usr/bin/env python3

import requests
import json

# Test data
test_data = {
    "income_statement": {
        "revenue_sales": {"2022": 683795, "2023": 700075},
        "cogs": {"2022": 523940, "2023": 529105},
        "operating_expenses": {"2022": 131218, "2023": 143983},
        "operating_profit_ebit": {"2022": 29798, "2023": 34473},
        "interest_expense": {"2022": 8768, "2023": 8078},
        "interest_income": {"2022": 16706, "2023": 4562},
        "net_income": {"2022": 51407, "2023": 35964}
    },
    "balance_sheet": {
        "cash_equivalents": {"2022": 48586, "2023": 17623},
        "accounts_receivable": {"2022": 36473, "2023": 78674},
        "inventory": {"2022": 256002, "2023": 243959},
        "ppe": {"2022": 67605, "2023": 71747},
        "accounts_payable": {"2022": 186078, "2023": 163061},
        "shareholders_equity": {"2022": 305119, "2023": 326417}
    },
    "cash_flow_statement": {
        "cash_flow_from_operations": {"2022": 26952, "2023": -2917},
        "capital_expenditures": {"2022": -9171, "2023": -13084},
        "taxes_paid": {"2022": 34112, "2023": 40093},
        "interest_paid": {"2022": 8427, "2023": 6895}
    }
}

def test_health():
    print("Testing health endpoint...")
    try:
        response = requests.get("http://localhost:5000/valuation/health")
        print(f"Health Status: {response.status_code}")
        print(f"Health Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Health test failed: {e}")
        return False

def test_simple_endpoint():
    print("\nTesting simple test endpoint...")
    try:
        simple_data = {"test": "data"}
        response = requests.post(
            "http://localhost:5000/valuation/test",
            json=simple_data,
            headers={"Content-Type": "application/json"}
        )
        print(f"Test Status: {response.status_code}")
        print(f"Test Response: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Simple test failed: {e}")
        return False

def test_valuation():
    print("\nTesting valuation endpoint...")
    try:
        response = requests.post(
            "http://localhost:5000/valuation/evaluate",
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        print(f"Valuation Status: {response.status_code}")
        print(f"Valuation Response: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Valuation test failed: {e}")
        return False

if __name__ == "__main__":
    print("Starting valuation endpoint tests...\n")
    
    if test_health():
        print("✅ Health check passed")
    else:
        print("❌ Health check failed")
        
    if test_simple_endpoint():
        print("✅ Simple test passed")
    else:
        print("❌ Simple test failed")
        
    if test_valuation():
        print("✅ Valuation test passed")
    else:
        print("❌ Valuation test failed")
        
    print("\nTest completed.")
