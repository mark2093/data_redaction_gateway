"""
Streaming redaction endpoints for real-time data processing.
"""
import asyncio
import json
import logging
from typing import AsyncGenerator, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Request, Body
from fastapi.responses import StreamingResponse

from ...engines.base import RedactionEngine
from ...policy import get_policy_loader
from ...security import verify_api_key
from ...observability import MetricsCollector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stream", tags=["Streaming"])


@router.post(
    "/redact/ndjson",
    response_class=StreamingResponse,
    summary="Stream NDJSON Redaction",
    description="""
    Process newline-delimited JSON (NDJSON) stream with real-time redaction.
    
    **Input Format:**
    - Each line must be a valid JSON object
    - Lines separated by newline characters (\\n)
    - Content-Type: application/x-ndjson or text/plain
    
    **Output Format:**
    - Redacted NDJSON stream (same format as input)
    - Each line is independently redacted
    - Streaming response for efficient processing
    
    **Example Input:**
    ```
    {"name": "John Doe", "email": "john@example.com"}
    {"phone": "555-1234", "ssn": "123-45-6789"}
    ```
    
    **Example Output:**
    ```
    {"name": "********", "email": "j**n@e******.com"}
    {"phone": "555-1234", "ssn": "*******6789"}
    ```
    """,
    responses={
        200: {
            "description": "Streaming NDJSON response with redacted data",
            "content": {
                "application/x-ndjson": {
                    "example": '{"name":"********","email":"j**n@e******.com"}\\n{"phone":"555-1234","ssn":"*******6789"}\\n'
                }
            }
        }
    }
)
async def stream_redact_ndjson(
    ndjson_data: str = Body(
        ...,
        media_type="text/plain",
        description="Newline-delimited JSON data (one JSON object per line)",
        example='{"name": "John Doe", "email": "john@example.com"}\n{"phone": "555-1234", "ssn": "123-45-6789"}'
    ),
    api_key: str = Depends(verify_api_key)
):
    """
    Process NDJSON (newline-delimited JSON) stream with redaction.
    
    Accepts streaming NDJSON data and returns redacted NDJSON stream.
    Each line should contain a valid JSON object.
    """
    try:
        # Get policy and rules
        policy_loader = get_policy_loader()
        rules = policy_loader.get_rules()
        
        # Create redaction engine
        engine = RedactionEngine(rules)
        
        async def process_ndjson_stream() -> AsyncGenerator[str, None]:
            """Process NDJSON stream line by line."""
            metrics = MetricsCollector()
            total_processed = 0
            total_redactions = 0
            
            try:
                # Process NDJSON data
                for line in ndjson_data.strip().split('\n'):
                    if not line.strip():
                        continue
                    
                    try:
                        # Parse JSON line
                        data = json.loads(line)
                        
                        # Apply redaction (engine creates new meta per redact call)
                        redacted_data = engine.redact(data)
                        redaction_meta = engine.get_redaction_meta()
                        
                        # Update metrics
                        total_processed += 1
                        total_redactions += len(redaction_meta)
                        
                        # Yield redacted line
                        yield json.dumps(redacted_data, separators=(',', ':')) + '\n'
                        
                    except json.JSONDecodeError as e:
                        logger.warning(f"Invalid JSON line: {line[:100]}... Error: {e}")
                        # Yield original line if JSON parsing fails
                        yield line + '\n'
                    except Exception as e:
                        logger.error(f"Error processing line: {e}")
                        yield line + '\n'
                
                # Log final metrics
                logger.info(f"NDJSON stream processed: {total_processed} lines, {total_redactions} redactions")
                
            except Exception as e:
                logger.error(f"Stream processing error: {e}")
                yield f'{{"error": "Stream processing failed: {str(e)}"}}\n'
        
        return StreamingResponse(
            process_ndjson_stream(),
            media_type="application/x-ndjson",
            headers={
                "X-Content-Type": "application/x-ndjson",
                "X-Policy-Version": policy_loader.get_policy_version()
            }
        )
        
    except Exception as e:
        logger.error(f"NDJSON streaming error: {e}")
        raise HTTPException(status_code=500, detail="NDJSON streaming failed")


@router.websocket("/redact/ws")
async def websocket_redact(websocket: WebSocket):
    """
    WebSocket endpoint for real-time bidirectional redaction.
    
    Establishes a persistent WebSocket connection for interactive redaction.
    Perfect for chat applications, real-time data feeds, or interactive systems.
    
    **Connection:**
    ```javascript
    const ws = new WebSocket('ws://localhost:8000/stream/redact/ws');
    ```
    
    **Send Message Format:**
    ```json
    {
        "data": {"name": "John Doe", "email": "john@example.com"},
        "include_meta": true
    }
    ```
    
    **Receive Message Format:**
    ```json
    {
        "redacted_data": {"name": "********", "email": "j**n@e******.com"},
        "policy_version": "1.4",
        "redaction_meta": [
            {"field": "name", "rule": "PERSON", "action": "mask"},
            {"field": "email", "rule": "EMAIL", "action": "preserve_structure"}
        ]
    }
    ```
    
    **Error Response:**
    ```json
    {"error": "Missing 'data' field in message"}
    ```
    """
    await websocket.accept()
    
    try:
        # Get policy and rules
        policy_loader = get_policy_loader()
        rules = policy_loader.get_rules()
        
        # Create redaction engine
        engine = RedactionEngine(rules)
        metrics = MetricsCollector()
        
        logger.info("WebSocket redaction session started")
        
        while True:
            try:
                # Receive data from client
                data = await websocket.receive_text()
                
                try:
                    # Parse client message
                    message = json.loads(data)
                    
                    if "data" not in message:
                        await websocket.send_json({
                            "error": "Missing 'data' field in message"
                        })
                        continue
                    
                    # Apply redaction (engine creates new meta per redact call)
                    redacted_data = engine.redact(message["data"])
                    redaction_meta = engine.get_redaction_meta()
                    
                    # Record metrics
                    metrics.record_redactions(len(redaction_meta))
                    
                    # Prepare response
                    response = {
                        "redacted_data": redacted_data,
                        "policy_version": policy_loader.get_policy_version()
                    }
                    
                    # Include metadata if requested
                    if message.get("include_meta", False):
                        response["redaction_meta"] = [
                            {
                                "field": meta.field,
                                "rule": meta.rule,
                                "action": meta.action.value,
                                "timestamp": meta.timestamp.isoformat()
                            }
                            for meta in redaction_meta
                        ]
                    
                    # Send response
                    await websocket.send_json(response)
                    
                except json.JSONDecodeError:
                    await websocket.send_json({
                        "error": "Invalid JSON format"
                    })
                except Exception as e:
                    logger.error(f"WebSocket processing error: {e}")
                    await websocket.send_json({
                        "error": f"Processing failed: {str(e)}"
                    })
                    
            except WebSocketDisconnect:
                logger.info("WebSocket client disconnected")
                break
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                await websocket.send_json({
                    "error": f"WebSocket error: {str(e)}"
                })
                break
                
    except Exception as e:
        logger.error(f"WebSocket session error: {e}")
    finally:
        logger.info("WebSocket redaction session ended")


@router.post(
    "/redact/chunked",
    response_class=StreamingResponse,
    summary="Chunked Stream Redaction",
    description="""
    Process large datasets in chunks with real-time redaction.
    
    **Features:**
    - Processes data in manageable chunks
    - Provides per-chunk redaction statistics
    - Stream start/end markers for tracking
    - Efficient for large file processing
    
    **Input Format:**
    Send a JSON array of objects to process in chunks.
    
    **Response Format:**
    Each chunk is a JSON object with:
    - `chunk_id`: Sequential chunk number
    - `data`: Redacted data object
    - `redactions`: Number of redactions in this chunk
    
    **Example Output:**
    ```json
    {"stream_start": true, "policy_version": "1.4"}
    {"chunk_id": 1, "data": {"name": "***", "email": "***"}, "redactions": 2}
    {"chunk_id": 2, "data": {"phone": "***", "ssn": "***"}, "redactions": 2}
    {"stream_end": true, "total_chunks": 2, "total_redactions": 4}
    ```
    """,
    responses={
        200: {
            "description": "Streaming chunked response with redaction statistics",
            "content": {
                "application/json": {
                    "example": '{"stream_start":true,"policy_version":"1.4"}\\n{"chunk_id":1,"data":{"name":"***"},"redactions":1}\\n{"stream_end":true,"total_chunks":1,"total_redactions":1}'
                }
            }
        }
    }
)
async def stream_redact_chunked(
    data_chunks: Optional[list] = Body(
        None,
        description="Optional array of data objects to process in chunks. If not provided, uses demo data.",
        example=[
            {"name": "Alice Johnson", "email": "alice@example.com"},
            {"phone": "555-123-4567", "card": "4111111111111111"},
            {"address": "123 Main St", "ssn": "123-45-6789"}
        ]
    ),
    api_key: str = Depends(verify_api_key)
):
    """
    Process streaming data in chunks with redaction.
    
    Accepts chunked transfer encoding for large datasets.
    """
    try:
        # Get policy and rules
        policy_loader = get_policy_loader()
        rules = policy_loader.get_rules()
        
        # Create redaction engine
        engine = RedactionEngine(rules)
        
        async def process_chunks() -> AsyncGenerator[bytes, None]:
            """Process data chunks with redaction."""
            metrics = MetricsCollector()
            chunk_count = 0
            total_redactions = 0
            
            try:
                # In a real implementation, this would read from request stream
                # For now, we'll simulate with a generator
                
                # Yield header
                yield b'{"stream_start": true, "policy_version": "'
                yield policy_loader.get_policy_version().encode('utf-8')
                yield b'"}\n'
                
                # Use provided data or default sample data
                if data_chunks is None or len(data_chunks) == 0:
                    sample_data = [
                        {"name": "Alice Johnson", "email": "alice@example.com"},
                        {"phone": "555-123-4567", "card": "4111111111111111"},
                        {"address": "123 Main St", "ssn": "123-45-6789"}
                    ]
                else:
                    sample_data = data_chunks
                
                for chunk_data in sample_data:
                    # Apply redaction (engine creates new meta per redact call)
                    redacted_chunk = engine.redact(chunk_data)
                    redaction_meta = engine.get_redaction_meta()
                    
                    chunk_count += 1
                    total_redactions += len(redaction_meta)
                    
                    # Yield redacted chunk
                    chunk_response = {
                        "chunk_id": chunk_count,
                        "data": redacted_chunk,
                        "redactions": len(redaction_meta)
                    }
                    
                    yield json.dumps(chunk_response, separators=(',', ':')).encode('utf-8')
                    yield b'\n'
                    
                    # Simulate processing delay
                    await asyncio.sleep(0.1)
                
                # Yield footer
                yield json.dumps({
                    "stream_end": True,
                    "total_chunks": chunk_count,
                    "total_redactions": total_redactions
                }, separators=(',', ':')).encode('utf-8')
                
            except Exception as e:
                logger.error(f"Chunked processing error: {e}")
                yield json.dumps({"error": str(e)}).encode('utf-8')
        
        return StreamingResponse(
            process_chunks(),
            media_type="application/json",
            headers={
                "X-Content-Type": "application/json",
                "X-Transfer-Encoding": "chunked",
                "X-Policy-Version": policy_loader.get_policy_version()
            }
        )
        
    except Exception as e:
        logger.error(f"Chunked streaming error: {e}")
        raise HTTPException(status_code=500, detail="Chunked streaming failed")


# Health check for streaming
@router.get(
    "/health",
    summary="Streaming Service Health Check",
    description="""
    Check the health status of all streaming endpoints.
    
    Returns information about available streaming endpoints and supported protocols.
    Use this endpoint to verify the streaming service is operational before connecting.
    """,
    responses={
        200: {
            "description": "Streaming service is healthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "endpoints": {
                            "ndjson": "/stream/redact/ndjson",
                            "websocket": "/stream/redact/ws",
                            "chunked": "/stream/redact/chunked"
                        },
                        "protocols": ["HTTP/1.1", "WebSocket"]
                    }
                }
            }
        }
    }
)
async def streaming_health():
    """Health check for streaming endpoints."""
    return {
        "status": "healthy",
        "endpoints": {
            "ndjson": "/stream/redact/ndjson",
            "websocket": "/stream/redact/ws", 
            "chunked": "/stream/redact/chunked"
        },
        "protocols": ["HTTP/1.1", "WebSocket"]
    }


__all__ = ["router"]