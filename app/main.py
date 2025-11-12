"""Main FastAPI application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.routes import transactions, health, auth, metrics
from app.middleware import (
    RequestIDMiddleware,
    LoggingMiddleware,
    TimeoutMiddleware,
    MetricsMiddleware,
    RateLimitMiddleware
)
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.contextvars.merge_contextvars,  # Include request context
        structlog.processors.JSONRenderer()
    ]
)

app = FastAPI(
    title="AstroPay Activity Feed API",
    description="Unified Activity Feed API for consolidating financial transactions",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Middleware order matters! Add in reverse order of execution
# Request ID must be first to track all requests
app.add_middleware(RequestIDMiddleware)

# Logging middleware (after request ID)
app.add_middleware(LoggingMiddleware)

# Metrics middleware (for Prometheus)
app.add_middleware(MetricsMiddleware)

# Timeout middleware
app.add_middleware(TimeoutMiddleware, timeout=settings.request_timeout)

# Rate limiting middleware (before CORS to reject early)
if settings.rate_limit_enabled:
    app.add_middleware(RateLimitMiddleware)

# CORS middleware (should be last)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(transactions.router, prefix=settings.api_prefix)
app.include_router(health.router, prefix=settings.api_prefix)
app.include_router(metrics.router, prefix=settings.api_prefix)


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger = structlog.get_logger()
    logger.info("Starting AstroPay Activity Feed API", version="1.0.0")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    from app.api.dependencies import get_event_service
    event_service = get_event_service()
    event_service.close()
    logger = structlog.get_logger()
    logger.info("Shutting down AstroPay Activity Feed API")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "AstroPay Activity Feed API",
        "version": "1.0.0",
        "docs": "/docs"
    }

