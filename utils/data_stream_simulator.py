"""
Data Stream Simulator for PII/PCI Redaction Gateway.

Simulates real-time data streams by sending requests to the FastAPI endpoints.
Generates various types of data (orders, transactions, chat messages) with
embedded PII/PCI data for testing the redaction service.
"""
import asyncio
import httpx
import json
import logging
import random
import sys
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from faker import Faker
from pathlib import Path

# Add parent directory to path to import config
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.config_loader import get_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Faker
fake = Faker()

# Load configuration
app_config = get_config()


class DataStreamSimulator:
    """Simulates real-time data streams to the redaction gateway."""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        """
        Initialize the simulator.
        
        Args:
            base_url: Base URL of the redaction API (defaults to config)
            api_key: API key for authentication (defaults to config)
        """
        self.base_url = base_url or f"http://{app_config.server.host}:{app_config.server.port}"
        self.api_key = api_key or (app_config.security.api_keys[0] if app_config.security.api_keys else "dev-api-key-12345")
        self.headers = {
            app_config.security.api_key_header_name: self.api_key,
            "Content-Type": "application/json"
        }

                
    def generate_order_data(self) -> Dict[str, Any]:
        """
        Generate e-commerce order data with PII.
        
        Returns:
            Order data dictionary
        """
        return {
            "order_id": f"ORD-{random.randint(100000, 999999)}",
            "customer": {
                "name": fake.name(),
                "email": fake.email(),
                "phone": fake.phone_number(),
                "billing_address": fake.address().replace('\n', ', '),
                "credit_card": fake.credit_card_number(),
                "expiry": fake.credit_card_expire(),
                "cvv": str(random.randint(100, 999))
            },
            "order_date": datetime.utcnow().isoformat(),
            "amount": round(random.uniform(10.0, 5000.0), 2),
            "currency": random.choice(["USD", "EUR", "GBP"]),
            "notes": fake.sentence()
        }
        
    def generate_transaction_data(self) -> Dict[str, Any]:
        """
        Generate financial transaction data with PCI data.
        
        Returns:
            Transaction data dictionary
        """
        return {
            "txn_id": f"TXN-{random.randint(1000000, 9999999)}",
            "account_no": fake.bban(),
            "iban": fake.iban(),
            "pan": fake.credit_card_number(),
            "amount": round(random.uniform(100.0, 10000.0), 2),
            "currency": random.choice(["USD", "EUR", "GBP"]),
            "merchant": fake.company(),
            "customer_name": fake.name(),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def generate_chat_message(self) -> Dict[str, Any]:
        """
        Generate chat message with embedded PII.
        
        Returns:
            Chat message dictionary
        """
        templates = [
            f"Hi, this is {fake.name()}, my card {fake.credit_card_number()} was declined today.",
            f"My phone number is {fake.phone_number()}, please contact me about the refund.",
            f"Hello, my email is {fake.email()} and I can't log into my account.",
            f"I need help with transaction {fake.credit_card_number()}. Contact me at {fake.phone_number()}.",
            f"My account {fake.bban()} shows incorrect balance. Email: {fake.email()}",
        ]
        
        return {
            "chat_id": f"C{random.randint(10000, 99999)}",
            "timestamp": datetime.utcnow().isoformat(),
            "message": random.choice(templates)
        }
    
    async def send_request(
        self,
        endpoint: str,
        data: Dict[str, Any],
        session: httpx.AsyncClient
    ) -> Optional[Dict[str, Any]]:
        """
        Send a single request to the API.
        
        Args:
            endpoint: API endpoint path
            data: Request data
            session: HTTP client session
            
        Returns:
            Response data or None on error
        """
        try:
            url = f"{self.base_url}{endpoint}"
            
            # Prepare request payload
            payload = {
                "data": data,
                "include_meta": True
            }
            
            response = await session.post(
                url,
                json=payload,
                headers=self.headers,
                timeout=30.0
            )
            
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error: {e}")
            return None
        except Exception as e:
            logger.error(f"Request error: {e}")
            return None
    
    async def simulate_stream(
        self,
        data_type: str,
        count: int,
        interval_ms: int = 1000,
        endpoint: str = "/redact"
    ):
        """
        Simulate a stream of data.
        
        Args:
            data_type: Type of data to generate (order, transaction, chat)
            count: Number of records to send
            interval_ms: Interval between requests in milliseconds
            endpoint: API endpoint to use
        """
        logger.info(f"Starting {data_type} stream: {count} records, {interval_ms}ms interval")
        
        async with httpx.AsyncClient() as session:
            for i in range(count):
                # Generate data based on type
                if data_type == "order":
                    data = self.generate_order_data()
                elif data_type == "transaction":
                    data = self.generate_transaction_data()
                elif data_type == "chat":
                    data = self.generate_chat_message()
                else:
                    logger.error(f"Unknown data type: {data_type}")
                    continue
                
                # Send request
                logger.info(f"Sending {data_type} record {i+1}/{count}")
                response = await self.send_request(endpoint, data, session)
                
                if response:
                    # Log summary
                    redaction_count = len(response.get('redaction_meta', []))
                    processing_time = response.get('processing_time_ms', 0)
                    
                    logger.info(
                        f"✓ Processed: {redaction_count} redactions, "
                        f"{processing_time:.2f}ms"
                    )
                else:
                    logger.warning(f"✗ Failed to process record {i+1}")
                
                # Wait before next request
                if i < count - 1:
                    await asyncio.sleep(interval_ms / 1000.0)
        
        logger.info(f"Completed {data_type} stream")
    
    async def simulate_mixed_stream(
        self,
        count: int,
        interval_ms: int = 500
    ):
        """
        Simulate mixed stream with all data types.
        
        Args:
            count: Total number of records to send
            interval_ms: Interval between requests in milliseconds
        """
        logger.info(f"Starting mixed stream: {count} records, {interval_ms}ms interval")
        
        data_types = ["order", "transaction", "chat"]
        
        async with httpx.AsyncClient() as session:
            for i in range(count):
                # Randomly select data type
                data_type = random.choice(data_types)
                
                # Generate data
                if data_type == "order":
                    data = self.generate_order_data()
                elif data_type == "transaction":
                    data = self.generate_transaction_data()
                else:  # chat
                    data = self.generate_chat_message()
                
                # Send request
                logger.info(f"Sending {data_type} record {i+1}/{count}")
                response = await self.send_request("/redact", data, session)
                
                if response:
                    redaction_count = len(response.get('redaction_meta', []))
                    processing_time = response.get('processing_time_ms', 0)
                    
                    logger.info(
                        f"✓ {data_type}: {redaction_count} redactions, "
                        f"{processing_time:.2f}ms"
                    )
                else:
                    logger.warning(f"✗ Failed: {data_type} record {i+1}")
                
                # Wait before next request
                if i < count - 1:
                    await asyncio.sleep(interval_ms / 1000.0)
        
        logger.info("Completed mixed stream")
    
    async def run_load_test(
        self,
        duration_seconds: int = 60,
        requests_per_second: int = 10
    ):
        """
        Run a load test.
        
        Args:
            duration_seconds: Test duration in seconds
            requests_per_second: Target RPS
        """
        logger.info(
            f"Starting load test: {duration_seconds}s duration, "
            f"{requests_per_second} RPS"
        )
        
        start_time = time.time()
        total_requests = 0
        successful_requests = 0
        failed_requests = 0
        
        interval_ms = 1000 / requests_per_second
        
        async with httpx.AsyncClient() as session:
            while (time.time() - start_time) < duration_seconds:
                # Generate random data
                data_type = random.choice(["order", "transaction", "chat"])
                
                if data_type == "order":
                    data = self.generate_order_data()
                elif data_type == "transaction":
                    data = self.generate_transaction_data()
                else:
                    data = self.generate_chat_message()
                
                # Send request
                response = await self.send_request("/redact", data, session)
                
                total_requests += 1
                if response:
                    successful_requests += 1
                else:
                    failed_requests += 1
                
                # Wait to maintain RPS
                await asyncio.sleep(interval_ms / 1000.0)
        
        # Summary
        elapsed = time.time() - start_time
        actual_rps = total_requests / elapsed
        success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 0
        
        logger.info("=" * 60)
        logger.info("Load Test Summary")
        logger.info("=" * 60)
        logger.info(f"Duration: {elapsed:.2f}s")
        logger.info(f"Total Requests: {total_requests}")
        logger.info(f"Successful: {successful_requests}")
        logger.info(f"Failed: {failed_requests}")
        logger.info(f"Success Rate: {success_rate:.2f}%")
        logger.info(f"Actual RPS: {actual_rps:.2f}")
        logger.info("=" * 60)


async def main():
    """Main entry point for simulator."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Data Stream Simulator")
    parser.add_argument(
        "--mode",
        choices=["order", "transaction", "chat", "mixed", "load"],
        default="mixed",
        help="Simulation mode"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=10,
        help="Number of records to send"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=1000,
        help="Interval between requests in milliseconds"
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="Base URL of the API"
    )
    parser.add_argument(
        "--api-key",
        default="dev-api-key-12345",
        help="API key for authentication"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=60,
        help="Load test duration in seconds"
    )
    parser.add_argument(
        "--rps",
        type=int,
        default=10,
        help="Requests per second for load test"
    )
    
    args = parser.parse_args()
    
    # Create simulator
    simulator = DataStreamSimulator(base_url=args.url, api_key=args.api_key)
    
    # Run simulation based on mode
    if args.mode == "load":
        await simulator.run_load_test(
            duration_seconds=args.duration,
            requests_per_second=args.rps
        )
    elif args.mode == "mixed":
        await simulator.simulate_mixed_stream(
            count=args.count,
            interval_ms=args.interval
        )
    else:
        await simulator.simulate_stream(
            data_type=args.mode,
            count=args.count,
            interval_ms=args.interval
        )


if __name__ == "__main__":
    asyncio.run(main())
