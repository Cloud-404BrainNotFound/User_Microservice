import time
import logging
import uuid
from fastapi import Request
from typing import Callable
from contextvars import ContextVar

# Create a context variable to store correlation ID
correlation_id_ctx_var = ContextVar("correlation_id", default=None)
logger = logging.getLogger("service_logger")

def get_correlation_id():
    return correlation_id_ctx_var.get()

async def logging_dependency(request: Request, call_next: Callable):
    # Check if correlation ID exists in request headers
    correlation_id = request.headers.get("x-correlation-id")
    if not correlation_id:
        # Generate a new correlation ID only if not present
        correlation_id = str(uuid.uuid4())
    
    correlation_id_ctx_var.set(correlation_id)
    
    start_time = time.time()
    
    # Extract service information from request
    service_port = request.url.port
    
    # Add correlation ID to request headers for downstream services
    request.headers.__dict__["_list"].append(
        (b"x-correlation-id", correlation_id.encode())
    )
    
    # Log request with correlation ID
    logger.info(
        f"Request started - Method: {request.method} Path: {request.url.path}",
        extra={
            "correlation_id": correlation_id,
            "port": service_port,
            "method": request.method,
            "path": request.url.path
        }
    )

    try:
        response = await call_next(request)
        
        process_time = (time.time() - start_time) * 1000
        logger.info(
            f"Request completed - Method: {request.method} Path: {request.url.path} Status: {response.status_code}",
            extra={
                "correlation_id": correlation_id,
                "port": service_port,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": f"{process_time:.2f}"
            }
        )
        
        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id
        return response
        
    except Exception as e:
        logger.error(
            f"Request failed - Method: {request.method} Path: {request.url.path}",
            extra={
                "correlation_id": correlation_id,
                "port": service_port,
                "method": request.method,
                "path": request.url.path,
                "error": str(e)
            }
        )
        raise
    finally:
        # Clean up context var
        correlation_id_ctx_var.set(None)