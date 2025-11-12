"""Transaction API routes."""
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from typing import Optional, Union
from datetime import datetime
from uuid import UUID
from app.schemas import (
    TransactionCreate,
    TransactionResponse,
    TransactionFilter,
    PaginationParams,
    PaginatedResponse,
    CursorPaginationParams,
    CursorPaginatedResponse,
    TransactionType,
    Product,
    TransactionStatus
)
from app.api.dependencies import get_transaction_service
from app.services.transaction_service import TransactionService
from app.services.elasticsearch_transaction_service import ElasticsearchTransactionService
from typing import Union
from app.auth import get_current_user_id, get_current_user_id_optional
from app.config import settings
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("", response_model=TransactionResponse, status_code=201)
async def create_transaction(
    transaction: TransactionCreate,
    current_user_id: Optional[str] = Depends(get_current_user_id_optional),
    service: Union[TransactionService, ElasticsearchTransactionService] = Depends(get_transaction_service)
):
    """
    Create a new transaction.
    
    The user_id from the JWT token will override the user_id in the request body
    to ensure users can only create transactions for themselves.
    """
    try:
        # Override user_id from token if authentication is enabled
        if current_user_id:
            transaction.user_id = current_user_id
            logger.info("User ID overridden from JWT token", user_id=current_user_id)
        
        return service.create_transaction(transaction)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to create transaction", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("", response_model=Union[PaginatedResponse, CursorPaginatedResponse])
async def get_transactions(
    transaction_type: Optional[TransactionType] = Query(None, description="Filter by transaction type"),
    product: Optional[Product] = Query(None, description="Filter by product"),
    status: Optional[TransactionStatus] = Query(None, description="Filter by status"),
    currency: Optional[str] = Query(None, description="Filter by currency"),
    start_date: Optional[datetime] = Query(None, description="Start date filter (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="End date filter (ISO format)"),
    min_amount: Optional[float] = Query(None, description="Minimum amount"),
    max_amount: Optional[float] = Query(None, description="Maximum amount"),
    search_query: Optional[str] = Query(None, description="Freeform text search"),
    # Metadata filters - common fields
    direction: Optional[str] = Query(None, description="P2P direction: 'sent' or 'received'"),
    merchant_name: Optional[str] = Query(None, description="Card payment merchant name"),
    card_last_four: Optional[str] = Query(None, description="Card last four digits (e.g., '5678')"),
    peer_name: Optional[str] = Query(None, description="P2P peer name"),
    # Offset-based pagination (for backward compatibility)
    page: Optional[int] = Query(None, ge=1, description="Page number (offset-based pagination)"),
    page_size: Optional[int] = Query(None, ge=1, le=100, description="Page size (offset-based pagination)"),
    # Cursor-based pagination (recommended for new clients)
    cursor: Optional[str] = Query(None, description="Cursor for pagination (cursor-based pagination)"),
    limit: Optional[int] = Query(None, ge=1, le=100, description="Number of items per page (cursor-based pagination)"),
    # user_id only for development/testing when there's no JWT
    user_id: Optional[str] = Query(None, description="User ID (only for development/testing without JWT)"),
    current_user_id: Optional[str] = Depends(get_current_user_id_optional),
    service: Union[TransactionService, ElasticsearchTransactionService] = Depends(get_transaction_service)
):
    """
    Get transactions with filters and pagination.
    
    **Authentication:**
    - If JWT token is provided in Authorization header, user_id is extracted from the token
    - If no token is provided, user_id must be passed as query parameter (for development/testing only)
    - When authenticated, users can only access their own transactions
    
    **Example with JWT (Recommended):**
    ```
    GET /api/v1/transactions?search_query=John
    Authorization: Bearer <token>
    ```
    Note: No need to pass user_id when using JWT - it's extracted from the token.
    
    **Example without JWT (development only):**
    ```
    GET /api/v1/transactions?user_id=user123&search_query=John&page=1&page_size=20
    ```
    """
    # Determine which user_id to use - prioritize JWT token over query parameter
    if current_user_id:
        # User is authenticated via JWT - use token's user_id
        effective_user_id = current_user_id
        # If user_id was also provided in query, ignore it (security: use token's user_id)
        if user_id and user_id != current_user_id:
            logger.warning(
                "User provided user_id in query but is authenticated via JWT. Using JWT user_id.",
                jwt_user_id=current_user_id,
                query_user_id=user_id
            )
    elif user_id:
        # No JWT token, but user_id provided in query (development/testing mode)
        effective_user_id = user_id.strip()
    else:
        # Neither JWT nor query parameter provided
        raise HTTPException(
            status_code=400,
            detail=(
                "user_id is required. "
                "Provide it either via JWT token in Authorization header "
                "or as query parameter (for development/testing only)."
            )
        )
    
    effective_user_id = effective_user_id.strip()
    
    if not effective_user_id:
        raise HTTPException(
            status_code=400,
            detail="user_id cannot be empty"
        )
    
    # Build metadata filters from query parameters
    metadata_filters = {}
    if direction:
        metadata_filters["direction"] = direction
    if merchant_name:
        metadata_filters["merchant_name"] = merchant_name
    if card_last_four:
        metadata_filters["card_last_four"] = card_last_four
    if peer_name:
        metadata_filters["peer_name"] = peer_name
    
    filters = TransactionFilter(
        user_id=effective_user_id,
        transaction_type=transaction_type,
        product=product,
        status=status,
        currency=currency,
        start_date=start_date,
        end_date=end_date,
        min_amount=min_amount,
        max_amount=max_amount,
        search_query=search_query,
        metadata_filters=metadata_filters if metadata_filters else None
    )
    
    # Determine which pagination method to use
    # Priority: cursor-based if cursor or limit is provided, otherwise offset-based
    use_cursor_pagination = cursor is not None or (limit is not None and page is None)
    
    try:
        if use_cursor_pagination:
            # Cursor-based pagination
            cursor_pagination = CursorPaginationParams(
                cursor=cursor,
                limit=limit if limit else 20
            )
            return service.get_transactions_cursor(
                user_id=effective_user_id,
                filters=filters,
                cursor_pagination=cursor_pagination
            )
        else:
            # Offset-based pagination (backward compatibility)
            pagination = PaginationParams(
                page=page if page else 1,
                page_size=page_size if page_size else 20
            )
            return service.get_transactions(
                user_id=effective_user_id,
                filters=filters,
                pagination=pagination
            )
    except Exception as e:
        logger.error("Failed to get transactions", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: str = Path(..., description="Transaction ID (UUID)"),
    current_user_id: Optional[str] = Depends(get_current_user_id_optional),
    service: Union[TransactionService, ElasticsearchTransactionService] = Depends(get_transaction_service)
):
    """
    Get a single transaction by ID.
    
    The transaction_id must be a valid UUID.
    If authenticated, users can only access their own transactions.
    """
    # Validate UUID format - this prevents path parameter from matching query strings
    try:
        uuid_obj = UUID(transaction_id)
        transaction_id = str(uuid_obj)  # Normalize UUID format
    except ValueError:
        # If it's not a valid UUID, it might be a query parameter that was incorrectly routed
        # Return a helpful error message
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid transaction ID format. Expected UUID, got: '{transaction_id}'. "
                "If you're trying to search, use query parameters: "
                "/api/v1/transactions?search_query=..."
            )
        )
    
    transaction = service.get_transaction(transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Security: If authenticated, ensure user can only access their own transaction
    if current_user_id and transaction.user_id != current_user_id:
        logger.warning(
            "User attempted to access another user's transaction",
            authenticated_user=current_user_id,
            transaction_user=transaction.user_id,
            transaction_id=transaction_id
        )
        raise HTTPException(
            status_code=403,
            detail="You can only access your own transactions"
        )
    
    return transaction

