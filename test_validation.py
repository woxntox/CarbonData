#!/usr/bin/env python3
"""
Test script to verify name validation works correctly
"""
import requests
import json

def test_name_validation():
    """Test various name inputs to ensure validation works"""
    base_url = "http://localhost:5003"
    
    test_cases = [
        # Valid names
        ("Matthew", "Valid name"),
        ("Alice", "Valid name"),
        ("Bob123", "Valid name with numbers"),
        
        # Invalid names - too long
        ("A" * 51, "Name too long"),
        
        # Invalid names - dangerous characters
        ("../hacker", "Path traversal attempt"),
        ("<script>alert('xss')</script>", "XSS attempt"),
        ("user|admin", "Pipe character"),
        ("test:name", "Colon character"),
        ("file>name", "Greater than character"),
        ("name<test", "Less than character"),
        ("test*name", "Asterisk character"),
        ("name?test", "Question mark character"),
        ("test\"name", "Quote character"),
        ("name\\test", "Backslash character"),
        
        # Invalid names - suspicious patterns
        ("javascript:alert(1)", "JavaScript protocol"),
        ("data:text/html,<script>alert(1)</script>", "Data URI with script"),
        ("<img src=x onerror=alert(1)>", "HTML injection"),
        ("<script>alert('xss')</script>", "Script tag"),
        ("<iframe src=javascript:alert(1)></iframe>", "Iframe injection"),
    ]
    
    print("Testing name validation...")
    print("=" * 50)
    
    for name, description in test_cases:
        try:
            response = requests.post(
                f"{base_url}/game/set_name",
                json={"name": name},
                timeout=5
            )
            
            data = response.json()
            
            if response.status_code == 200:
                print(f"❌ FAIL: '{name}' ({description}) - Should have been rejected")
            else:
                print(f"✅ PASS: '{name}' ({description}) - Correctly rejected: {data.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"❌ ERROR testing '{name}': {e}")
    
    print("=" * 50)
    print("Validation test complete!")

if __name__ == "__main__":
    test_name_validation()
