"""Dependencies for API routes."""
from functools import lru_cache
from fastapi import Depends
from sqlalchemy.orm import Session
from typing import Union
from app.database import get_db
from app.services.cache_service import CacheService
from app.services.search_service import SearchService
from app.services.event_service import EventService
from app.services.transaction_service import TransactionService
from app.services.elasticsearch_transaction_service import ElasticsearchTransactionService
from app.config import settings


@lru_cache()
def get_cache_service() -> CacheService:
    """Get cache service singleton."""
    return CacheService()


@lru_cache()
def get_search_service() -> SearchService:
    """Get search service singleton."""
    return SearchService()


@lru_cache()
def get_event_service() -> EventService:
    """Get event service singleton."""
    return EventService()


def get_transaction_service(
    db: Session = Depends(get_db)
) -> Union[TransactionService, ElasticsearchTransactionService]:
    """
    Get transaction service with dependencies.
    
    If use_elasticsearch_as_primary is True, returns ElasticsearchTransactionService.
    Otherwise, returns TransactionService (uses PostgreSQL as primary).
    """
    cache_service = get_cache_service()
    search_service = get_search_service()
    
    if settings.use_elasticsearch_as_primary and search_service.enabled:
        # Use Elasticsearch as primary data source
        return ElasticsearchTransactionService(
            search_service=search_service,
            cache_service=cache_service
        )
    else:
        # Use PostgreSQL as primary data source (default)
        return TransactionService(
            db=db,
            cache_service=cache_service,
            search_service=search_service,
            event_service=get_event_service()
        )

