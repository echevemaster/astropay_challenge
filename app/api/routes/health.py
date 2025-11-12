"""Health check routes."""
from fastapi import APIRouter, Depends
from app.schemas import HealthCheckResponse
from app.database import engine
from app.api.dependencies import get_cache_service, get_search_service, get_event_service
from app.services.cache_service import CacheService
from app.services.search_service import SearchService
from app.services.event_service import EventService
from app.middleware.circuit_breaker import (
    get_elasticsearch_breaker,
    get_redis_breaker,
    get_kafka_breaker
)
from sqlalchemy import text

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthCheckResponse)
async def health_check(
    cache_service: CacheService = Depends(get_cache_service),
    search_service: SearchService = Depends(get_search_service),
    event_service: EventService = Depends(get_event_service)
):
    """Health check endpoint."""
    # Check database
    db_status = "healthy"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        db_status = "unhealthy"
    
    # Check cache
    cache_status = "healthy" if cache_service.health_check() else "unhealthy"
    redis_breaker_state = get_redis_breaker().get_state()
    if redis_breaker_state["state"] == "open":
        cache_status = "degraded"
    
    # Check search
    search_status = "healthy" if search_service.health_check() else "unhealthy"
    es_breaker_state = get_elasticsearch_breaker().get_state()
    if es_breaker_state["state"] == "open":
        search_status = "degraded"
    
    # Check event service (Kafka)
    event_status = "healthy" if event_service.health_check() else "unhealthy"
    kafka_breaker_state = get_kafka_breaker().get_state()
    if kafka_breaker_state["state"] == "open":
        event_status = "degraded"
    
    # Overall status: healthy if all critical services are healthy
    # degraded if some are degraded but database is healthy
    # unhealthy if database is unhealthy
    if db_status == "unhealthy":
        overall_status = "unhealthy"
    elif all([cache_status == "healthy", search_status == "healthy", event_status == "healthy"]):
        overall_status = "healthy"
    else:
        overall_status = "degraded"
    
    return HealthCheckResponse(
        status=overall_status,
        database=db_status,
        redis=cache_status,
        elasticsearch=search_status,
        kafka=event_status
    )

