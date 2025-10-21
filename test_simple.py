#!/usr/bin/env python3
"""
Simple test to check name validation
"""
import requests

def test_simple():
    """Test simple name validation"""
    try:
        response = requests.post(
            "http://localhost:5003/game/set_name",
            json={"name": "Matthew"},
            timeout=5
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_simple()
