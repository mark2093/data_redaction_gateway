"""
Content decompression and decoding middleware for handling encoded request bodies.
"""
import base64
import gzip
import zlib
import logging
from typing import Optional, Tuple, Union
from fastapi import Request, HTTPException

logger = logging.getLogger(__name__)


class ContentProcessingMiddleware:
    """Middleware for processing compressed and encoded content."""
    
    def __init__(self, max_content_length: int = 10 * 1024 * 1024):  # 10MB default
        """
        Initialize content processing middleware.
        
        Args:
            max_content_length: Maximum allowed content length after decompression
        """
        self.max_content_length = max_content_length
    
    async def process_request_body(self, request: Request) -> Tuple[bytes, str]:
        """
        Process request body with decompression and decoding.
        
        Args:
            request: FastAPI request object
            
        Returns:
            Tuple of (processed_body, content_type)
            
        Raises:
            HTTPException: If processing fails or content is too large
        """
        # Get raw body
        raw_body = await request.body()
        content_type = request.headers.get("content-type", "")
        content_encoding = request.headers.get("content-encoding", "")
        
        # Start with raw body
        processed_body = raw_body
        
        # Step 1: Handle content encoding (compression)
        if content_encoding:
            processed_body = await self._decompress_body(processed_body, content_encoding)
        
        # Step 2: Handle base64 encoding
        processed_body = await self._decode_base64_if_needed(processed_body, content_type)
        
        # Step 3: Check final size
        if len(processed_body) > self.max_content_length:
            raise HTTPException(
                status_code=413,
                detail=f"Content too large after processing: {len(processed_body)} bytes"
            )
        
        return processed_body, content_type
    
    async def _decompress_body(self, body: bytes, encoding: str) -> bytes:
        """
        Decompress body based on content encoding.
        
        Args:
            body: Compressed body data
            encoding: Content encoding type
            
        Returns:
            Decompressed body data
            
        Raises:
            HTTPException: If decompression fails
        """
        try:
            encoding_lower = encoding.lower().strip()
            
            if encoding_lower == "gzip":
                logger.debug("Decompressing gzip content")
                return gzip.decompress(body)
            
            elif encoding_lower == "deflate":
                logger.debug("Decompressing deflate content")
                try:
                    # Try with zlib first
                    return zlib.decompress(body)
                except zlib.error:
                    # Try raw deflate
                    return zlib.decompress(body, -zlib.MAX_WBITS)
            
            elif encoding_lower == "br":
                logger.debug("Decompressing brotli content")
                try:
                    import brotli
                    return brotli.decompress(body)
                except ImportError:
                    raise HTTPException(
                        status_code=415,
                        detail="Brotli compression not supported (brotli package not installed)"
                    )
            
            elif encoding_lower == "identity" or encoding_lower == "":
                # No compression
                return body
            
            else:
                logger.warning(f"Unsupported content encoding: {encoding}")
                raise HTTPException(
                    status_code=415,
                    detail=f"Unsupported content encoding: {encoding}"
                )
                
        except Exception as e:
            logger.error(f"Decompression error for encoding '{encoding}': {e}")
            if isinstance(e, HTTPException):
                raise
            raise HTTPException(
                status_code=400,
                detail=f"Failed to decompress content: {str(e)}"
            )
    
    async def _decode_base64_if_needed(self, body: bytes, content_type: str) -> bytes:
        """
        Decode base64 content if it appears to be base64 encoded.
        
        Args:
            body: Request body data
            content_type: Content type header
            
        Returns:
            Decoded body data (or original if not base64)
        """
        try:
            # Check if content type indicates base64
            if "base64" in content_type.lower():
                logger.debug("Decoding base64 content (content-type indicates base64)")
                return base64.b64decode(body)
            
            # Heuristic: if body is text and looks like base64, try to decode
            if self._looks_like_base64(body):
                logger.debug("Attempting base64 decode (content looks like base64)")
                try:
                    decoded = base64.b64decode(body, validate=True)
                    # If successful and result looks like meaningful data, use it
                    if self._looks_like_meaningful_data(decoded):
                        return decoded
                except Exception:
                    pass  # Not base64 or invalid, continue with original
            
            return body
            
        except Exception as e:
            logger.warning(f"Base64 decode attempt failed: {e}")
            return body
    
    def _looks_like_base64(self, data: bytes) -> bool:
        """
        Heuristic to determine if data looks like base64.
        
        Args:
            data: Data to check
            
        Returns:
            True if data might be base64 encoded
        """
        if len(data) < 4:
            return False
        
        try:
            # Check if data is text
            text = data.decode('ascii')
            
            # Check if it has base64 characteristics
            # - Only contains base64 characters
            # - Length is multiple of 4 (with potential padding)
            import string
            base64_chars = string.ascii_letters + string.digits + '+/='
            
            if not all(c in base64_chars for c in text):
                return False
            
            # Check padding
            if text.endswith('=='):
                return len(text) % 4 == 0
            elif text.endswith('='):
                return len(text) % 4 == 0
            else:
                return len(text) % 4 == 0
                
        except UnicodeDecodeError:
            return False
    
    def _looks_like_meaningful_data(self, data: bytes) -> bool:
        """
        Heuristic to determine if decoded data looks meaningful.
        
        Args:
            data: Decoded data to check
            
        Returns:
            True if data appears to be meaningful (JSON, text, etc.)
        """
        if len(data) < 2:
            return False
        
        # Check if it starts with common data formats
        try:
            # JSON
            if data.startswith(b'{') or data.startswith(b'['):
                return True
            
            # XML
            if data.startswith(b'<'):
                return True
            
            # Plain text (high ratio of printable characters)
            try:
                text = data.decode('utf-8')
                printable_ratio = sum(c.isprintable() for c in text) / len(text)
                return printable_ratio > 0.7
            except UnicodeDecodeError:
                pass
            
            # Binary formats with headers
            if data.startswith(b'\x1f\x8b'):  # gzip
                return True
            if data.startswith(b'PK'):  # zip
                return True
            if data.startswith(b'\x89PNG'):  # PNG
                return True
            
        except Exception:
            pass
        
        return False


async def content_processing_middleware(request: Request, call_next):
    """
    FastAPI middleware function for content processing.
    
    Args:
        request: FastAPI request object
        call_next: Next middleware/handler in chain
        
    Returns:
        Response from next handler
    """
    # Only process requests with bodies
    if request.method not in ["POST", "PUT", "PATCH"]:
        return await call_next(request)
    
    # Only process if we have content
    content_length = request.headers.get("content-length")
    if not content_length or int(content_length) == 0:
        return await call_next(request)
    
    try:
        # Create processor
        processor = ContentProcessingMiddleware()
        
        # Process the body
        processed_body, content_type = await processor.process_request_body(request)
        
        # Replace request body if it was modified
        if processed_body != await request.body():
            # Store processed body in request state for later use
            request.state.processed_body = processed_body
            request.state.original_content_type = content_type
            
            logger.debug(f"Processed request body: {len(processed_body)} bytes")
        
        # Continue with next middleware/handler
        response = await call_next(request)
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Content processing middleware error: {e}")
        # Continue without processing on error
        return await call_next(request)


# Helper function to get processed body from request
def get_processed_body(request: Request) -> Optional[bytes]:
    """
    Get processed body from request state.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Processed body if available, None otherwise
    """
    return getattr(request.state, 'processed_body', None)


def get_original_content_type(request: Request) -> Optional[str]:
    """
    Get original content type from request state.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Original content type if available, None otherwise
    """
    return getattr(request.state, 'original_content_type', None)


__all__ = [
    "ContentProcessingMiddleware",
    "content_processing_middleware", 
    "get_processed_body",
    "get_original_content_type"
]