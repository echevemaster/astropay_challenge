"""Pydantic schemas for request/response validation."""
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from enum import Enum


class TransactionType(str, Enum):
    """Transaction type enumeration."""
    CARD = "card"
    P2P = "p2p"
    CRYPTO = "crypto"
    TOP_UP = "top_up"
    WITHDRAWAL = "withdrawal"
    BILL_PAYMENT = "bill_payment"
    EARNINGS = "earnings"


class Product(str, Enum):
    """Product enumeration."""
    CARD = "Card"
    P2P = "P2P"
    CRYPTO = "Crypto"
    EARNINGS = "Earnings"


class TransactionStatus(str, Enum):
    """Transaction status enumeration."""
    COMPLETED = "completed"
    PENDING = "pending"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TransactionMetadata(BaseModel):
    """Base metadata schema - can be extended per transaction type."""
    model_config = ConfigDict(extra="allow")


class CardPaymentMetadata(TransactionMetadata):
    """Metadata for card payment transactions."""
    merchant_name: Optional[str] = None
    merchant_category: Optional[str] = None
    card_last_four: Optional[str] = None
    location: Optional[str] = None


class P2PTransferMetadata(TransactionMetadata):
    """Metadata for P2P transfer transactions."""
    peer_name: Optional[str] = None
    peer_email: Optional[str] = None
    peer_phone: Optional[str] = None
    direction: Optional[str] = None  # sent, received


class TransactionBase(BaseModel):
    """Base transaction schema."""
    user_id: str
    transaction_type: TransactionType
    product: Product
    status: TransactionStatus
    currency: str
    amount: float
    metadata: Optional[Dict[str, Any]] = None


class TransactionCreate(TransactionBase):
    """Schema for creating a transaction."""
    pass


class TransactionResponse(TransactionBase):
    """Schema for transaction response."""
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )
    
    @model_validator(mode='before')
    @classmethod
    def map_custom_metadata(cls, data):
        """Map custom_metadata from database to metadata for API."""
        if isinstance(data, dict):
            if 'custom_metadata' in data and 'metadata' not in data:
                data['metadata'] = data.pop('custom_metadata')
        elif hasattr(data, 'custom_metadata'):
            # For SQLAlchemy models
            data_dict = {
                'id': data.id,
                'user_id': data.user_id,
                'transaction_type': data.transaction_type,
                'product': data.product,
                'status': data.status,
                'currency': data.currency,
                'amount': float(data.amount),
                'metadata': data.custom_metadata,
                'created_at': data.created_at,
                'updated_at': data.updated_at,
            }
            return data_dict
        return data


class TransactionFilter(BaseModel):
    """Filter parameters for transaction queries."""
    user_id: Optional[str] = None
    transaction_type: Optional[TransactionType] = None
    product: Optional[Product] = None
    status: Optional[TransactionStatus] = None
    currency: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    search_query: Optional[str] = None  # Freeform text search
    metadata_filters: Optional[Dict[str, Any]] = None  # Custom metadata filters


class PaginationParams(BaseModel):
    """Pagination parameters for offset-based pagination."""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class CursorPaginationParams(BaseModel):
    """Pagination parameters for cursor-based pagination."""
    cursor: Optional[str] = Field(None, description="Cursor for pagination (base64 encoded)")
    limit: int = Field(default=20, ge=1, le=100, description="Number of items per page")


class PaginatedResponse(BaseModel):
    """Paginated response wrapper for offset-based pagination."""
    items: List[TransactionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class CursorPaginatedResponse(BaseModel):
    """Paginated response wrapper for cursor-based pagination."""
    items: List[TransactionResponse]
    next_cursor: Optional[str] = Field(None, description="Cursor for next page (base64 encoded)")
    has_more: bool = Field(description="Whether there are more items")
    limit: int = Field(description="Number of items requested")


class HealthCheckResponse(BaseModel):
    """Health check response."""
    status: str
    database: str
    redis: str
    elasticsearch: str
    kafka: str

