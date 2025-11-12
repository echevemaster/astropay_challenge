"""Database models for transactions."""
from sqlalchemy import Column, String, DateTime, Numeric, JSON, Index, Text, TypeDecorator
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.sql import func
import uuid
from app.database import Base


class GUID(TypeDecorator):
    """Platform-independent GUID type.
    
    Uses PostgreSQL's UUID type when available, otherwise uses String(36).
    """
    impl = String
    cache_ok = True
    
    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PostgresUUID(as_uuid=True))
        else:
            return dialect.type_descriptor(String(36))
    
    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            if isinstance(value, uuid.UUID):
                return str(value)
            return value
    
    def process_result_value(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            if isinstance(value, str):
                return uuid.UUID(value)
            return value


class Transaction(Base):
    """Transaction model representing unified activity feed entries."""
    
    __tablename__ = "transactions"
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False, index=True)
    transaction_type = Column(String(50), nullable=False, index=True)  # card, p2p, crypto, etc.
    product = Column(String(50), nullable=False, index=True)  # Card, P2P, Earnings, Crypto
    status = Column(String(50), nullable=False, index=True)  # completed, pending, failed
    currency = Column(String(10), nullable=False, index=True)
    amount = Column(Numeric(18, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Custom metadata as JSONB for flexible schema per transaction type
    custom_metadata = Column(JSON, nullable=True)
    
    # Full-text search content (denormalized for performance)
    search_content = Column(Text, nullable=True)
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_user_created', 'user_id', 'created_at'),
        Index('idx_type_status', 'transaction_type', 'status'),
        Index('idx_product_currency', 'product', 'currency'),
    )

