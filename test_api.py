#!/usr/bin/env python3
"""
MindEase API Testing Script
Tests the backend API endpoints to ensure everything is working correctly.
"""

import requests
import json
import sys

API_BASE_URL = "http://127.0.0.1:5000"

def print_header(text):
    """Print a formatted header"""
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60)

def print_success(text):
    """Print success message"""
    print(f"[OK] {text}")

def print_error(text):
    """Print error message"""
    print(f"[ERROR] {text}")

def test_server_status():
    """Test if the server is running"""
    print_header("Testing Server Status")
    try:
        response = requests.get(f"{API_BASE_URL}/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_success(f"Server is running: {data.get('message')}")
            print_success(f"Model loaded: {data.get('model_loaded')}")
            return True
        else:
            print_error(f"Server returned status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_error("Cannot connect to server. Is it running on port 5000?")
        return False
    except Exception as e:
        print_error(f"Error: {str(e)}")
        return False

def test_prediction(journal_text, expected_risk=None):
    """Test the prediction endpoint"""
    print(f"\nTesting prediction for: '{journal_text[:50]}...'")
    try:
        response = requests.post(
            f"{API_BASE_URL}/predict",
            json={"journal": journal_text},
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            risk = data.get('risk')
            confidence = data.get('confidence')
            
            print_success(f"Risk Level: {risk}")
            if confidence:
                print_success(f"Confidence: {confidence:.2%}")
            
            if expected_risk and risk != expected_risk:
                print(f"  Note: Expected {expected_risk}, got {risk}")
            
            return True
        else:
            print_error(f"Request failed with status: {response.status_code}")
            print(f"  Response: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Error: {str(e)}")
        return False

def test_error_handling():
    """Test error handling"""
    print_header("Testing Error Handling")
    
    # Test empty request
    print("\nTesting empty request...")
    try:
        response = requests.post(
            f"{API_BASE_URL}/predict",
            json={},
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        if response.status_code == 400:
            print_success("Empty request properly rejected")
        else:
            print_error(f"Unexpected status code: {response.status_code}")
    except Exception as e:
        print_error(f"Error: {str(e)}")
    
    # Test empty journal
    print("\nTesting empty journal text...")
    try:
        response = requests.post(
            f"{API_BASE_URL}/predict",
            json={"journal": ""},
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        if response.status_code == 400:
            print_success("Empty journal properly rejected")
        else:
            print_error(f"Unexpected status code: {response.status_code}")
    except Exception as e:
        print_error(f"Error: {str(e)}")

def run_all_tests():
    """Run all tests"""
    print_header("MindEase API Test Suite")
    print("Testing backend API functionality...\n")
    
    # Test 1: Server Status
    if not test_server_status():
        print("\n" + "="*60)
        print("Cannot proceed with tests. Please start the server first:")
        print("  cd ai-depression-risk-assessment/backend")
        print("  python app.py")
        print("="*60)
        sys.exit(1)
    
    # Test 2: Predictions
    print_header("Testing Predictions")
    
    test_cases = [
        ("I'm feeling great today! Life is wonderful and I'm so happy.", "Low"),
        ("I feel sad and lonely. Nothing seems to matter anymore.", "High"),
        ("I'm a bit stressed about work but managing okay.", "Moderate"),
        ("Everything is going well. I'm excited about the future!", "Low"),
        ("I can't sleep, I feel hopeless, and I don't want to do anything.", "High"),
    ]
    
    passed = 0
    for text, expected in test_cases:
        if test_prediction(text, expected):
            passed += 1
    
    print(f"\nPrediction Tests: {passed}/{len(test_cases)} passed")
    
    # Test 3: Error Handling
    test_error_handling()
    
    # Summary
    print_header("Test Summary")
    print_success("All critical tests completed!")
    print("\nNext steps:")
    print("  1. Open index.html in your browser")
    print("  2. Create an account and login")
    print("  3. Try the journal analysis feature")
    print("\n" + "="*60)

if __name__ == "__main__":
    try:
        run_all_tests()
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user.")
        sys.exit(0)
