"""Enhanced logging middleware."""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import time
import structlog
from typing import Callable

logger = structlog.get_logger()


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request/response logging."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request and response details."""
        start_time = time.time()
        
        # Extract request details
        method = request.method
        path = request.url.path
        query_params = str(request.query_params) if request.query_params else ""
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        request_id = getattr(request.state, "request_id", None)
        user_id = getattr(request.state, "user_id", None)
        
        # Log request
        logger.info(
            "Incoming request",
            method=method,
            path=path,
            query_params=query_params,
            client_ip=client_ip,
            user_agent=user_agent,
            request_id=request_id,
            user_id=user_id
        )
        
        # Process request
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            # Log successful response
            logger.info(
                "Request completed",
                method=method,
                path=path,
                status_code=response.status_code,
                process_time=round(process_time, 4),
                request_id=request_id,
                user_id=user_id
            )
            
            # Add process time header
            response.headers["X-Process-Time"] = str(round(process_time, 4))
            
            return response
        except Exception as e:
            process_time = time.time() - start_time
            
            # Log error
            logger.error(
                "Request failed",
                method=method,
                path=path,
                error=str(e),
                error_type=type(e).__name__,
                process_time=round(process_time, 4),
                request_id=request_id,
                user_id=user_id,
                exc_info=True
            )
            raise

