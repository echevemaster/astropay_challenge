"""Request timeout middleware."""
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import asyncio
from app.config import settings
import structlog

logger = structlog.get_logger()


class TimeoutMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce request timeouts."""
    
    def __init__(self, app, timeout: int = 30):
        super().__init__(app)
        self.timeout = timeout
        # Per-endpoint timeouts
        self.endpoint_timeouts = {
            "/api/v1/transactions": 10,  # 10 seconds for transaction queries
            "/api/v1/auth/token": 5,  # 5 seconds for auth
            "/api/v1/health": 2,  # 2 seconds for health checks
        }
    
    async def dispatch(self, request: Request, call_next):
        """Process request with timeout."""
        path = request.url.path
        timeout = self.endpoint_timeouts.get(path, self.timeout)
        
        try:
            # Wrap the call_next in a timeout
            response = await asyncio.wait_for(
                call_next(request),
                timeout=timeout
            )
            return response
        except asyncio.TimeoutError:
            request_id = getattr(request.state, "request_id", None)
            logger.warning(
                "Request timeout",
                path=path,
                timeout=timeout,
                request_id=request_id
            )
            return JSONResponse(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                content={
                    "error": "Request timeout",
                    "message": f"Request exceeded {timeout}s timeout",
                    "path": path
                }
            )

