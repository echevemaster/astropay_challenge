"""Transaction service using Elasticsearch as primary data source."""
from typing import List, Optional
from app.schemas import (
    TransactionResponse,
    TransactionFilter,
    PaginationParams,
    PaginatedResponse,
    CursorPaginationParams,
    CursorPaginatedResponse
)
from app.services.cache_service import CacheService
from app.services.search_service import SearchService
from app.utils.cursor import encode_cursor, decode_cursor
from app.middleware.circuit_breaker import get_elasticsearch_breaker
from datetime import datetime
import structlog

logger = structlog.get_logger()


class ElasticsearchTransactionService:
    """Service for transactions using Elasticsearch as primary data source."""
    
    def __init__(
        self,
        search_service: SearchService,
        cache_service: CacheService
    ):
        self.search_service = search_service
        self.cache_service = cache_service
    
    def get_transactions(
        self,
        user_id: str,
        filters: Optional[TransactionFilter] = None,
        pagination: Optional[PaginationParams] = None
    ) -> PaginatedResponse:
        """Get transactions from Elasticsearch."""
        if not self.search_service.enabled:
            raise RuntimeError("Elasticsearch is not available")
        
        # Build cache key
        cache_key = self._build_cache_key(user_id, filters, pagination)
        
        # Try cache first
        cached_result = self.cache_service.get(cache_key)
        if cached_result:
            logger.debug("Cache hit", cache_key=cache_key)
            return PaginatedResponse(**cached_result)
        
        # Convert dates to ISO format strings
        start_date_str = filters.start_date.isoformat() if filters and filters.start_date else None
        end_date_str = filters.end_date.isoformat() if filters and filters.end_date else None
        
        # Build search filters
        search_filters = self._extract_search_filters(filters)
        
        # Search in Elasticsearch (return full documents)
        documents, total = self.search_service.search(
            user_id=user_id,
            query=filters.search_query if filters and filters.search_query else None,
            filters=search_filters,
            start_date=start_date_str,
            end_date=end_date_str,
            page=pagination.page if pagination else 1,
            page_size=pagination.page_size if pagination else 20,
            return_documents=True  # Get full documents, not just IDs
        )
        
        # Convert Elasticsearch documents to TransactionResponse
        items = []
        for doc in documents:
            try:
                # Convert ES document to TransactionResponse format
                transaction_dict = {
                    "id": doc.get("id"),
                    "user_id": doc.get("user_id"),
                    "transaction_type": doc.get("transaction_type"),
                    "product": doc.get("product"),
                    "status": doc.get("status"),
                    "currency": doc.get("currency"),
                    "amount": doc.get("amount"),
                    "created_at": doc.get("created_at"),
                    "metadata": doc.get("metadata", {}),
                }
                
                # Parse created_at if it's a string
                if isinstance(transaction_dict["created_at"], str):
                    transaction_dict["created_at"] = datetime.fromisoformat(
                        transaction_dict["created_at"].replace("Z", "+00:00")
                    )
                
                items.append(TransactionResponse.model_validate(transaction_dict))
            except Exception as e:
                logger.warning("Failed to parse Elasticsearch document", error=str(e), doc_id=doc.get("id"))
                continue
        
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
    
    def get_transactions_cursor(
        self,
        user_id: str,
        filters: Optional[TransactionFilter] = None,
        cursor_pagination: Optional[CursorPaginationParams] = None
    ) -> CursorPaginatedResponse:
        """Get transactions with cursor-based pagination from Elasticsearch."""
        if not self.search_service.enabled:
            raise RuntimeError("Elasticsearch is not available")
        
        # Build cache key
        cache_key = self._build_cache_key_cursor(user_id, filters, cursor_pagination)
        
        # Try cache first
        cached_result = self.cache_service.get(cache_key)
        if cached_result:
            logger.debug("Cache hit", cache_key=cache_key)
            return CursorPaginatedResponse(**cached_result)
        
        # Convert dates
        start_date_str = filters.start_date.isoformat() if filters and filters.start_date else None
        end_date_str = filters.end_date.isoformat() if filters and filters.end_date else None
        
        # Build search filters
        search_filters = self._extract_search_filters(filters)
        
        limit = cursor_pagination.limit if cursor_pagination else 20
        
        # Use search_after for cursor-based pagination in Elasticsearch
        # For simplicity, we'll fetch limit + 1 to check has_more
        documents, total = self.search_service.search(
            user_id=user_id,
            query=filters.search_query if filters and filters.search_query else None,
            filters=search_filters,
            start_date=start_date_str,
            end_date=end_date_str,
            page=1,  # We'll handle pagination manually
            page_size=limit + 1,  # Fetch one extra to check has_more
            return_documents=True
        )
        
        # Apply cursor filter if provided
        if cursor_pagination and cursor_pagination.cursor:
            cursor_data = decode_cursor(cursor_pagination.cursor)
            if cursor_data:
                cursor_created_at = cursor_data["created_at"]
                cursor_id = cursor_data["id"]
                
                # Filter documents after cursor
                filtered_docs = []
                for doc in documents:
                    doc_created_at = doc.get("created_at")
                    if isinstance(doc_created_at, str):
                        doc_created_at = datetime.fromisoformat(doc_created_at.replace("Z", "+00:00"))
                    
                    doc_id = doc.get("id", "")
                    
                    # Keep if created_at < cursor or (created_at == cursor and id < cursor_id)
                    if doc_created_at < cursor_created_at or (
                        doc_created_at == cursor_created_at and doc_id < cursor_id
                    ):
                        filtered_docs.append(doc)
                
                documents = filtered_docs
        
        # Check has_more
        has_more = len(documents) > limit
        documents = documents[:limit]
        
        # Convert to TransactionResponse
        items = []
        for doc in documents:
            try:
                transaction_dict = {
                    "id": doc.get("id"),
                    "user_id": doc.get("user_id"),
                    "transaction_type": doc.get("transaction_type"),
                    "product": doc.get("product"),
                    "status": doc.get("status"),
                    "currency": doc.get("currency"),
                    "amount": doc.get("amount"),
                    "created_at": doc.get("created_at"),
                    "metadata": doc.get("metadata", {}),
                }
                
                if isinstance(transaction_dict["created_at"], str):
                    transaction_dict["created_at"] = datetime.fromisoformat(
                        transaction_dict["created_at"].replace("Z", "+00:00")
                    )
                
                items.append(TransactionResponse.model_validate(transaction_dict))
            except Exception as e:
                logger.warning("Failed to parse Elasticsearch document", error=str(e))
                continue
        
        # Generate next cursor
        next_cursor = None
        if items and has_more:
            last_item = items[-1]
            next_cursor = encode_cursor(str(last_item.id), last_item.created_at)
        
        result = CursorPaginatedResponse(
            items=items,
            next_cursor=next_cursor,
            has_more=has_more,
            limit=limit
        )
        
        # Cache result
        self.cache_service.set(cache_key, result.model_dump(), ttl=300)
        
        return result
    
    def get_transaction(self, transaction_id: str) -> Optional[TransactionResponse]:
        """Get a single transaction by ID from Elasticsearch."""
        if not self.search_service.enabled:
            raise RuntimeError("Elasticsearch is not available")
        
        cache_key = f"transaction:{transaction_id}"
        
        # Try cache
        cached = self.cache_service.get(cache_key)
        if cached:
            return TransactionResponse(**cached)
        
        try:
            # Get document from Elasticsearch
            breaker = get_elasticsearch_breaker()
            response = breaker.call(
                self.search_service.es_client.get,
                index="transactions",
                id=transaction_id
            )
            
            doc = response["_source"]
            doc["id"] = response["_id"]
            
            # Convert to TransactionResponse
            transaction_dict = {
                "id": doc.get("id"),
                "user_id": doc.get("user_id"),
                "transaction_type": doc.get("transaction_type"),
                "product": doc.get("product"),
                "status": doc.get("status"),
                "currency": doc.get("currency"),
                "amount": doc.get("amount"),
                "created_at": doc.get("created_at"),
                "metadata": doc.get("metadata", {}),
            }
            
            if isinstance(transaction_dict["created_at"], str):
                transaction_dict["created_at"] = datetime.fromisoformat(
                    transaction_dict["created_at"].replace("Z", "+00:00")
                )
            
            response_obj = TransactionResponse.model_validate(transaction_dict)
            self.cache_service.set(cache_key, response_obj.model_dump())
            
            return response_obj
        except Exception as e:
            logger.warning("Transaction not found in Elasticsearch", transaction_id=transaction_id, error=str(e))
            return None
    
    def _extract_search_filters(self, filters: Optional[TransactionFilter]) -> dict:
        """Extract filters for Elasticsearch."""
        search_filters = {}
        
        if not filters:
            return search_filters
        
        if filters.transaction_type:
            search_filters["transaction_type"] = filters.transaction_type.value
        if filters.product:
            search_filters["product"] = filters.product.value
        if filters.status:
            search_filters["status"] = filters.status.value
        if filters.currency:
            search_filters["currency"] = filters.currency
        
        # Include metadata filters (for filtering in Elasticsearch)
        if filters.metadata_filters:
            search_filters["metadata_filters"] = filters.metadata_filters
        
        # Include amount filters if present
        if filters.min_amount is not None:
            search_filters["min_amount"] = filters.min_amount
        if filters.max_amount is not None:
            search_filters["max_amount"] = filters.max_amount
        
        return search_filters
    
    def _build_cache_key(
        self,
        user_id: str,
        filters: Optional[TransactionFilter],
        pagination: Optional[PaginationParams]
    ) -> str:
        """Build cache key from filters and pagination."""
        parts = [f"transactions:es:user:{user_id}"]
        
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
            if filters.metadata_filters:
                for key, value in filters.metadata_filters.items():
                    parts.append(f"meta:{key}:{value}")
        
        if pagination:
            parts.append(f"page:{pagination.page}:size:{pagination.page_size}")
        
        return ":".join(parts)
    
    def _build_cache_key_cursor(
        self,
        user_id: str,
        filters: Optional[TransactionFilter],
        cursor_pagination: Optional[CursorPaginationParams]
    ) -> str:
        """Build cache key from filters and cursor pagination."""
        parts = [f"transactions:es:user:{user_id}:cursor"]
        
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
            if filters.metadata_filters:
                for key, value in filters.metadata_filters.items():
                    parts.append(f"meta:{key}:{value}")
        
        if cursor_pagination:
            parts.append(f"limit:{cursor_pagination.limit}")
            if cursor_pagination.cursor:
                parts.append(f"cursor:{cursor_pagination.cursor[:20]}")
        
        return ":".join(parts)

