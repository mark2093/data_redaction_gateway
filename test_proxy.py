#!/usr/bin/env python3
"""
Test script for proxy functionality.
Creates a simple upstream server and tests the proxy redaction.
"""
import asyncio
import json
import logging
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn
import httpx
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_mock_upstream_server():
    """Create a mock upstream service for testing."""
    app = FastAPI(title="Mock Upstream Service")
    
    @app.get("/health")
    async def health():
        return {"status": "healthy", "service": "mock_upstream"}
    
    @app.post("/api/v1/users/")
    async def create_user(user_data: dict):
        """Mock user creation endpoint that returns user with ID."""
        logger.info(f"Upstream received: {user_data}")
        
        # Simulate processing and return user with ID
        user_data["user_id"] = "usr_12345"
        user_data["created_at"] = "2025-11-09T12:00:00Z"
        
        return {"success": True, "user": user_data}
    
    @app.post("/api/v1/payments/")
    async def process_payment(payment_data: dict):
        """Mock payment processing endpoint."""
        logger.info(f"Payment upstream received: {payment_data}")
        
        # Simulate payment processing
        payment_data["transaction_id"] = "txn_67890"
        payment_data["status"] = "completed"
        
        return {"success": True, "payment": payment_data}
    
    return app


async def test_proxy_functionality():
    """Test the proxy functionality with real requests."""
    
    # Test data with PII
    user_test_data = {
        "name": "John Doe",
        "email": "john.doe@example.com",
        "phone": "555-123-4567",
        "address": "123 Main St, Anytown, NY 12345"
    }
    
    payment_test_data = {
        "customer_name": "Jane Smith",
        "card_number": "4111111111111111",
        "cvv": "123",
        "amount": 99.99
    }
    
    # Wait for services to be ready
    await asyncio.sleep(2)
    
    async with httpx.AsyncClient() as client:
        # Test 1: User creation through proxy (should redact PII)
        logger.info("Testing user creation through proxy...")
        try:
            response = await client.post(
                "http://localhost:8000/api/v1/users/",
                json=user_test_data,
                headers={"X-API-Key": "dev-api-key-12345", "Content-Type": "application/json"},
                timeout=30
            )
            logger.info(f"User proxy response: {response.status_code}")
            logger.info(f"Response headers: {dict(response.headers)}")
            logger.info(f"Response body: {response.text}")
        except Exception as e:
            logger.error(f"User proxy test failed: {e}")
        
        # Test 2: Payment through proxy (should redact card data)
        logger.info("Testing payment through proxy...")
        try:
            response = await client.post(
                "http://localhost:8000/api/v1/payments/",
                json=payment_test_data,
                headers={"X-API-Key": "dev-api-key-12345", "Content-Type": "application/json"},
                timeout=30
            )
            logger.info(f"Payment proxy response: {response.status_code}")
            logger.info(f"Response headers: {dict(response.headers)}")
            logger.info(f"Response body: {response.text}")
        except Exception as e:
            logger.error(f"Payment proxy test failed: {e}")
        
        # Test 3: Direct redaction API (should work as before)
        logger.info("Testing direct redaction API...")
        try:
            response = await client.post(
                "http://localhost:8000/redact/",
                json={"data": user_test_data, "include_meta": True},
                headers={"X-API-Key": "dev-api-key-12345", "Content-Type": "application/json"},
                timeout=30
            )
            logger.info(f"Direct API response: {response.status_code}")
            logger.info(f"Response body: {response.text}")
        except Exception as e:
            logger.error(f"Direct API test failed: {e}")


async def run_upstream_server():
    """Run the mock upstream server."""
    app = create_mock_upstream_server()
    config = uvicorn.Config(app, host="127.0.0.1", port=3000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


async def main():
    """Main test function."""
    logger.info("Starting proxy functionality test...")
    
    # Start upstream server in background
    upstream_task = asyncio.create_task(run_upstream_server())
    
    # Wait a bit for upstream to start
    await asyncio.sleep(1)
    
    # Run tests
    test_task = asyncio.create_task(test_proxy_functionality())
    
    # Wait for tests to complete (or timeout)
    try:
        await asyncio.wait_for(test_task, timeout=60)
    except asyncio.TimeoutError:
        logger.error("Tests timed out")
    
    # Cleanup
    upstream_task.cancel()
    try:
        await upstream_task
    except asyncio.CancelledError:
        pass


if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Proxy Functionality Test")
    print("=" * 60)
    print()
    print("This test will:")
    print("1. Start a mock upstream service on port 3000")
    print("2. Test proxy routing through the redaction gateway")
    print("3. Verify that PII is redacted in requests/responses")
    print()
    print("Prerequisites:")
    print("- Redaction gateway running on port 8000")
    print("- Proxy mode enabled in config/proxy.yaml")
    print()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()