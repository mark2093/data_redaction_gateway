"""
Test script for content processing middleware functionality.
"""
import base64
import gzip
import json
import requests
import sys
from pathlib import Path

# Test data
test_data = {
    "data": "John Doe's credit card number is 4532-1234-5678-9012 and his SSN is 123-45-6789"
}

def test_base64_encoding():
    """Test base64 encoded content processing."""
    print("\n=== Testing Base64 Encoding ===")
    
    # Encode test data as base64
    json_data = json.dumps(test_data)
    encoded_data = base64.b64encode(json_data.encode('utf-8'))
    
    print(f"Original data size: {len(json_data)} bytes")
    print(f"Encoded data size: {len(encoded_data)} bytes")
    print(f"Encoded data (first 100 chars): {encoded_data[:100]}")
    
    try:
        # Send request with base64 encoded body
        response = requests.post(
            'http://localhost:8000/redact/',
            data=encoded_data,
            headers={
                'Content-Type': 'application/json; charset=utf-8; base64',
                'Authorization': 'Bearer test-api-key'
            }
        )
        
        print(f"Response status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Redacted data: {result.get('redacted_data')}")
            print(f"Redactions: {len(result.get('redaction_meta', []))}")
        else:
            print(f"Error: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")


def test_gzip_compression():
    """Test gzip compressed content processing."""
    print("\n=== Testing Gzip Compression ===")
    
    # Compress test data with gzip
    json_data = json.dumps(test_data).encode('utf-8')
    compressed_data = gzip.compress(json_data)
    
    print(f"Original data size: {len(json_data)} bytes")
    print(f"Compressed data size: {len(compressed_data)} bytes")
    print(f"Compression ratio: {len(compressed_data)/len(json_data):.2%}")
    
    try:
        # Send request with gzip compressed body
        response = requests.post(
            'http://localhost:8000/redact/',
            data=compressed_data,
            headers={
                'Content-Type': 'application/json',
                'Content-Encoding': 'gzip',
                'Authorization': 'Bearer test-api-key'
            }
        )
        
        print(f"Response status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Redacted data: {result.get('redacted_data')}")
            print(f"Redactions: {len(result.get('redaction_meta', []))}")
        else:
            print(f"Error: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")


def test_normal_request():
    """Test normal uncompressed request for comparison."""
    print("\n=== Testing Normal Request (Control) ===")
    
    try:
        response = requests.post(
            'http://localhost:8000/redact/',
            json=test_data,
            headers={'Authorization': 'Bearer test-api-key'}
        )
        
        print(f"Response status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Redacted data: {result.get('redacted_data')}")
            print(f"Redactions: {len(result.get('redaction_meta', []))}")
        else:
            print(f"Error: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")


def test_combined_base64_gzip():
    """Test base64 encoded gzip compressed content."""
    print("\n=== Testing Combined Base64 + Gzip ===")
    
    # Compress then encode
    json_data = json.dumps(test_data).encode('utf-8')
    compressed_data = gzip.compress(json_data)
    encoded_data = base64.b64encode(compressed_data)
    
    print(f"Original size: {len(json_data)} bytes")
    print(f"After gzip: {len(compressed_data)} bytes")
    print(f"After base64: {len(encoded_data)} bytes")
    
    try:
        response = requests.post(
            'http://localhost:8000/redact/',
            data=encoded_data,
            headers={
                'Content-Type': 'application/json; base64',
                'Content-Encoding': 'gzip',
                'Authorization': 'Bearer test-api-key'
            }
        )
        
        print(f"Response status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Redacted data: {result.get('redacted_data')}")
            print(f"Redactions: {len(result.get('redaction_meta', []))}")
        else:
            print(f"Error: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")


def main():
    """Run all content processing tests."""
    print("Content Processing Middleware Test Suite")
    print("="*50)
    
    # Check if server is running
    try:
        response = requests.get('http://localhost:8000/health')
        if response.status_code != 200:
            print("ERROR: Server not running or not healthy")
            return 1
        print("✓ Server is running and healthy")
    except requests.exceptions.RequestException:
        print("ERROR: Could not connect to server at http://localhost:8000")
        print("Please start the server with: python main_modular.py")
        return 1
    
    # Run tests
    test_normal_request()
    test_base64_encoding()
    test_gzip_compression()
    test_combined_base64_gzip()
    
    print("\n" + "="*50)
    print("Content processing middleware tests completed!")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())