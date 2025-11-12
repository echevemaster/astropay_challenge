"""Transaction service with business logic."""
from typing import List, Optional
from sqlalchemy.orm import Session
from app.repositories.transaction_repository import TransactionRepository
from app.strategies.transaction_strategy import TransactionStrategyFactory
from app.schemas import (
    TransactionCreate,
    TransactionResponse,
    TransactionFilter,
    PaginationParams,
    PaginatedResponse,
    CursorPaginationParams,
    CursorPaginatedResponse
)
from app.utils.cursor import encode_cursor
from app.services.cache_service import CacheService
from app.services.search_service import SearchService
from app.services.event_service import EventService
from app.models import Transaction
import structlog
import json

logger = structlog.get_logger()


class TransactionService:
    """Service for transaction business logic."""
    
    def __init__(
        self,
        db: Session,
        cache_service: CacheService,
        search_service: SearchService,
        event_service: EventService
    ):
        self.repository = TransactionRepository(db)
        self.cache_service = cache_service
        self.search_service = search_service
        self.event_service = event_service
    
    def create_transaction(self, transaction_data: TransactionCreate) -> TransactionResponse:
        """Create a new transaction."""
        # Get strategy for transaction type
        strategy = TransactionStrategyFactory.get_strategy(transaction_data.transaction_type.value)
        
        # Process metadata
        metadata = transaction_data.metadata.copy() if transaction_data.metadata else {}
        
        # Validate metadata
        if metadata:
            if not strategy.validate_metadata(metadata):
                raise ValueError(f"Invalid metadata for transaction type {transaction_data.transaction_type}")
            
            # Enrich metadata
            metadata = strategy.enrich_metadata(metadata)
        
        # Build search content
        search_content = strategy.build_search_content(transaction_data)
        
        # Prepare database record
        db_transaction = {
            "user_id": transaction_data.user_id,
            "transaction_type": transaction_data.transaction_type.value,
            "product": transaction_data.product.value,
            "status": transaction_data.status.value,
            "currency": transaction_data.currency,
            "amount": transaction_data.amount,
            "custom_metadata": metadata if metadata else None,
            "search_content": search_content,
        }
        
        # Create in database
        transaction = self.repository.create(db_transaction)
        
        # Index in Elasticsearch (async in production)
        transaction_dict = {
            "id": str(transaction.id),
            "user_id": transaction.user_id,
            "transaction_type": transaction.transaction_type,
            "product": transaction.product,
            "status": transaction.status,
            "currency": transaction.currency,
            "amount": float(transaction.amount),
            "created_at": transaction.created_at.isoformat(),
            "search_content": transaction.search_content,
            "metadata": transaction.custom_metadata,
        }
        self.search_service.index_transaction(transaction_dict)
        
        # Publish event
        self.event_service.publish_transaction_created(transaction_dict)
        
        # Invalidate cache for user
        self.cache_service.delete_pattern(f"transactions:user:{transaction_data.user_id}:*")
        
        return TransactionResponse.model_validate(transaction)
    
    def get_transactions(
        self,
        user_id: str,
        filters: Optional[TransactionFilter] = None,
        pagination: Optional[PaginationParams] = None
    ) -> PaginatedResponse:
        """Get transactions for a user with filters and pagination."""
        # Build cache key
        cache_key = self._build_cache_key(user_id, filters, pagination)
        
        # Try cache first
        cached_result = self.cache_service.get(cache_key)
        if cached_result:
            logger.debug("Cache hit", cache_key=cache_key)
            return PaginatedResponse(**cached_result)
        
        # If search query is provided, use Elasticsearch
        if filters and filters.search_query:
            if not self.search_service.enabled:
                logger.warning(
                    "Elasticsearch is not available, falling back to PostgreSQL search",
                    user_id=user_id,
                    search_query=filters.search_query
                )
                # Fallback to PostgreSQL search
                transactions, total = self.repository.get_by_user_id(
                    user_id=user_id,
                    filters=filters,
                    pagination=pagination
                )
            else:
                logger.info(
                    "Using Elasticsearch for search",
                    user_id=user_id,
                    search_query=filters.search_query
                )
                
                # Convert dates to ISO format strings for Elasticsearch
                start_date_str = filters.start_date.isoformat() if filters.start_date else None
                end_date_str = filters.end_date.isoformat() if filters.end_date else None
                
                transaction_ids, total = self.search_service.search(
                    user_id=user_id,
                    query=filters.search_query,
                    filters=self._extract_search_filters(filters),
                    start_date=start_date_str,
                    end_date=end_date_str,
                    page=pagination.page if pagination else 1,
                    page_size=pagination.page_size if pagination else 20
                )
                
                logger.debug(
                    "Elasticsearch search completed",
                    user_id=user_id,
                    results_count=len(transaction_ids),
                    total=total
                )
                
                # Fetch transactions from database by IDs
                transactions = []
                for tx_id in transaction_ids:
                    tx = self.repository.get_by_id(tx_id)
                    if tx:
                        transactions.append(tx)
        else:
            # Use database query
            transactions, total = self.repository.get_by_user_id(
                user_id=user_id,
                filters=filters,
                pagination=pagination
            )
        
        # Convert to response
        items = [TransactionResponse.model_validate(tx) for tx in transactions]
        
        page = pagination.page if pagination else 1
        page_size = pagination.page_size if pagination else 20
        total_pages = (total + page_size - 1) // page_size
        
        result = PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
        
        # Cache result
        self.cache_service.set(cache_key, result.model_dump())
        
        return result
    
    def get_transaction(self, transaction_id: str) -> Optional[TransactionResponse]:
        """Get a single transaction by ID."""
        cache_key = f"transaction:{transaction_id}"
        
        # Try cache
        cached = self.cache_service.get(cache_key)
        if cached:
            return TransactionResponse(**cached)
        
        transaction = self.repository.get_by_id(transaction_id)
        if not transaction:
            return None
        
        response = TransactionResponse.model_validate(transaction)
        self.cache_service.set(cache_key, response.model_dump())
        
        return response
    
    def _build_cache_key(
        self,
        user_id: str,
        filters: Optional[TransactionFilter],
        pagination: Optional[PaginationParams]
    ) -> str:
        """Build cache key from filters and pagination."""
        parts = [f"transactions:user:{user_id}"]
        
        if filters:
            if filters.transaction_type:
                parts.append(f"type:{filters.transaction_type.value}")
            if filters.product:
                parts.append(f"product:{filters.product.value}")
            if filters.status:
                parts.append(f"status:{filters.status.value}")
            if filters.currency:
                parts.append(f"currency:{filters.currency}")
            if filters.search_query:
                parts.append(f"search:{filters.search_query}")
        
        if pagination:
            parts.append(f"page:{pagination.page}:size:{pagination.page_size}")
        
        return ":".join(parts)
    
    def _extract_search_filters(self, filters: TransactionFilter) -> dict:
        """Extract filters for Elasticsearch."""
        search_filters = {}
        if filters.transaction_type:
            search_filters["transaction_type"] = filters.transaction_type.value
        if filters.product:
            search_filters["product"] = filters.product.value
        if filters.status:
            search_filters["status"] = filters.status.value
        if filters.currency:
            search_filters["currency"] = filters.currency
        return search_filters
    
    def get_transactions_cursor(
        self,
        user_id: str,
        filters: Optional[TransactionFilter] = None,
        cursor_pagination: Optional[CursorPaginationParams] = None
    ) -> CursorPaginatedResponse:
        """Get transactions for a user with filters and cursor-based pagination."""
        # Build cache key
        cache_key = self._build_cache_key_cursor(user_id, filters, cursor_pagination)
        
        # Try cache first
        cached_result = self.cache_service.get(cache_key)
        if cached_result:
            logger.debug("Cache hit", cache_key=cache_key)
            return CursorPaginatedResponse(**cached_result)
        
        # If search query is provided, use Elasticsearch
        # Note: Elasticsearch search_after could be used for cursor-based pagination
        # For now, we'll use offset-based for Elasticsearch searches with cursor
        if filters and filters.search_query:
            if not self.search_service.enabled:
                logger.warning(
                    "Elasticsearch is not available, falling back to PostgreSQL search",
                    user_id=user_id,
                    search_query=filters.search_query
                )
                transactions, has_more = self.repository.get_by_user_id_cursor(
                    user_id=user_id,
                    filters=filters,
                    cursor_pagination=cursor_pagination
                )
            else:
                logger.info(
                    "Using Elasticsearch for search (with cursor fallback)",
                    user_id=user_id,
                    search_query=filters.search_query
                )
                # For Elasticsearch with cursor, we'll fetch all matching IDs first
                # then apply cursor pagination in memory (not ideal, but works)
                # In production, you'd want to implement search_after in Elasticsearch
                start_date_str = filters.start_date.isoformat() if filters.start_date else None
                end_date_str = filters.end_date.isoformat() if filters.end_date else None
                
                # Get a larger set of IDs from Elasticsearch
                limit = cursor_pagination.limit if cursor_pagination else 20
                transaction_ids, _ = self.search_service.search(
                    user_id=user_id,
                    query=filters.search_query,
                    filters=self._extract_search_filters(filters),
                    start_date=start_date_str,
                    end_date=end_date_str,
                    page=1,
                    page_size=limit * 2  # Get more to handle cursor pagination
                )
                
                # Fetch transactions and apply cursor pagination
                all_transactions = []
                for tx_id in transaction_ids:
                    tx = self.repository.get_by_id(tx_id)
                    if tx:
                        all_transactions.append(tx)
                
                # Sort by created_at DESC, id DESC
                all_transactions.sort(key=lambda x: (x.created_at, x.id), reverse=True)
                
                # Apply cursor filter if provided
                if cursor_pagination and cursor_pagination.cursor:
                    from app.utils.cursor import decode_cursor
                    cursor_data = decode_cursor(cursor_pagination.cursor)
                    if cursor_data:
                        cursor_created_at = cursor_data["created_at"]
                        cursor_id = cursor_data["id"]
                        all_transactions = [
                            tx for tx in all_transactions
                            if tx.created_at < cursor_created_at or
                            (tx.created_at == cursor_created_at and str(tx.id) < cursor_id)
                        ]
                
                # Apply limit and check has_more
                has_more = len(all_transactions) > limit
                transactions = all_transactions[:limit]
        else:
            # Use database query with cursor pagination
            transactions, has_more = self.repository.get_by_user_id_cursor(
                user_id=user_id,
                filters=filters,
                cursor_pagination=cursor_pagination
            )
        
        # Convert to response
        items = [TransactionResponse.model_validate(tx) for tx in transactions]
        
        # Generate next cursor from last item
        next_cursor = None
        if transactions and has_more:
            last_transaction = transactions[-1]
            next_cursor = encode_cursor(str(last_transaction.id), last_transaction.created_at)
        
        limit = cursor_pagination.limit if cursor_pagination else 20
        
        result = CursorPaginatedResponse(
            items=items,
            next_cursor=next_cursor,
            has_more=has_more,
            limit=limit
        )
        
        # Cache result (with shorter TTL for cursor-based pagination)
        self.cache_service.set(cache_key, result.model_dump(), ttl=300)  # 5 minutes
        
        return result
    
    def _build_cache_key_cursor(
        self,
        user_id: str,
        filters: Optional[TransactionFilter],
        cursor_pagination: Optional[CursorPaginationParams]
    ) -> str:
        """Build cache key from filters and cursor pagination."""
        parts = [f"transactions:user:{user_id}:cursor"]
        
        if filters:
            if filters.transaction_type:
                parts.append(f"type:{filters.transaction_type.value}")
            if filters.product:
                parts.append(f"product:{filters.product.value}")
            if filters.status:
                parts.append(f"status:{filters.status.value}")
            if filters.currency:
                parts.append(f"currency:{filters.currency}")
            if filters.search_query:
                parts.append(f"search:{filters.search_query}")
        
        if cursor_pagination:
            parts.append(f"limit:{cursor_pagination.limit}")
            if cursor_pagination.cursor:
                parts.append(f"cursor:{cursor_pagination.cursor[:20]}")  # First 20 chars for key
        
        return ":".join(parts)

