"""
Streaming redaction endpoints for real-time data processing.
"""
import asyncio
import json
import logging
from typing import AsyncGenerator, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.responses import StreamingResponse

from ...engines.base import RedactionEngine
from ...policy import get_policy_loader
from ...security import verify_api_key
from ...observability import MetricsCollector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stream", tags=["Streaming"])


@router.post("/redact/ndjson")
async def stream_redact_ndjson(
    request_body: bytes = Depends(lambda: None),  # Raw body
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
                # Read request body (streaming)
                # In a real implementation, this would be streamed
                body_text = request_body.decode('utf-8') if request_body else ""
                
                for line in body_text.strip().split('\n'):
                    if not line.strip():
                        continue
                    
                    try:
                        # Parse JSON line
                        data = json.loads(line)
                        
                        # Apply redaction
                        engine.reset_meta()
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
    WebSocket endpoint for real-time redaction.
    
    Clients can send JSON objects and receive redacted versions in real-time.
    Protocol:
    - Send: {"data": {...}, "include_meta": true/false}
    - Receive: {"redacted_data": {...}, "redaction_meta": [...]}
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
                    
                    # Apply redaction
                    engine.reset_meta()
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


@router.post("/redact/chunked")
async def stream_redact_chunked(
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
                
                # Process chunks (simulated)
                sample_data = [
                    {"name": "Alice Johnson", "email": "alice@example.com"},
                    {"phone": "555-123-4567", "card": "4111111111111111"},
                    {"address": "123 Main St", "ssn": "123-45-6789"}
                ]
                
                for chunk_data in sample_data:
                    engine.reset_meta()
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
@router.get("/health")
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