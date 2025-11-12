"""Repository pattern for transaction data access."""
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, String
from app.models import Transaction
from app.schemas import TransactionFilter, PaginationParams, CursorPaginationParams
from app.utils.cursor import decode_cursor
from datetime import datetime


class TransactionRepository:
    """Repository for transaction data access operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, transaction_data: dict) -> Transaction:
        """Create a new transaction."""
        transaction = Transaction(**transaction_data)
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)
        return transaction
    
    def get_by_id(self, transaction_id: str) -> Optional[Transaction]:
        """Get transaction by ID."""
        from uuid import UUID as UUIDType
        # Convert string to UUID if needed
        try:
            if isinstance(transaction_id, str):
                transaction_id = UUIDType(transaction_id)
        except (ValueError, AttributeError):
            pass  # Keep as string if conversion fails
        return self.db.query(Transaction).filter(Transaction.id == transaction_id).first()
    
    def get_by_user_id(
        self,
        user_id: str,
        filters: Optional[TransactionFilter] = None,
        pagination: Optional[PaginationParams] = None
    ) -> tuple[List[Transaction], int]:
        """Get transactions for a user with optional filters and offset-based pagination."""
        query = self.db.query(Transaction).filter(Transaction.user_id == user_id)
        
        if filters:
            query = self._apply_filters(query, filters)
        
        # Get total count before pagination
        total = query.count()
        
        # Apply pagination
        if pagination:
            offset = (pagination.page - 1) * pagination.page_size
            query = query.order_by(desc(Transaction.created_at), desc(Transaction.id))
            query = query.offset(offset).limit(pagination.page_size)
        else:
            query = query.order_by(desc(Transaction.created_at), desc(Transaction.id))
        
        return query.all(), total
    
    def get_by_user_id_cursor(
        self,
        user_id: str,
        filters: Optional[TransactionFilter] = None,
        cursor_pagination: Optional[CursorPaginationParams] = None
    ) -> Tuple[List[Transaction], bool]:
        """
        Get transactions for a user with optional filters and cursor-based pagination.
        
        Returns:
            Tuple of (transactions list, has_more boolean)
        """
        query = self.db.query(Transaction).filter(Transaction.user_id == user_id)
        
        if filters:
            query = self._apply_filters(query, filters)
        
        # Apply cursor-based pagination
        limit = cursor_pagination.limit if cursor_pagination else 20
        
        # Determine database dialect for consistent UUID handling
        from app.database import engine
        is_sqlite = engine.dialect.name == 'sqlite'
        
        if cursor_pagination and cursor_pagination.cursor:
            # Decode cursor
            cursor_data = decode_cursor(cursor_pagination.cursor)
            if cursor_data:
                from uuid import UUID as UUIDType
                cursor_created_at = cursor_data["created_at"]
                cursor_id = UUIDType(cursor_data["id"])
                
                # For cursor-based pagination with DESC ordering:
                # We want items that come AFTER the cursor in descending order
                # This means: created_at < cursor_created_at OR 
                #           (created_at == cursor_created_at AND id < cursor_id)
                # For SQLite, we need to compare UUIDs as strings for consistent ordering
                # For PostgreSQL, UUID comparison works natively
                if is_sqlite:
                    # Convert UUID to string for SQLite comparison
                    cursor_id_str = str(cursor_id)
                    # Use string comparison for consistent ordering
                    # For SQLite, we need to ensure datetime and UUID comparisons are consistent
                    query = query.filter(
                        or_(
                            Transaction.created_at < cursor_created_at,
                            and_(
                                Transaction.created_at == cursor_created_at,
                                func.cast(Transaction.id, String) < cursor_id_str
                            )
                        )
                    )
                else:
                    # PostgreSQL handles UUID comparison natively
                    query = query.filter(
                        or_(
                            Transaction.created_at < cursor_created_at,
                            and_(
                                Transaction.created_at == cursor_created_at,
                                Transaction.id < cursor_id
                            )
                        )
                    )
        
        # Order by created_at DESC, id DESC for consistent ordering
        # For SQLite, we need to ensure consistent ordering with string comparison
        if is_sqlite:
            # Use string cast for consistent ordering in SQLite
            # This ensures the ordering matches the comparison in the cursor filter
            query = query.order_by(
                desc(Transaction.created_at),
                desc(func.cast(Transaction.id, String))
            )
        else:
            # PostgreSQL handles UUID ordering natively
            query = query.order_by(desc(Transaction.created_at), desc(Transaction.id))
        
        # Fetch limit + 1 to check if there are more items
        transactions = query.limit(limit + 1).all()
        
        # Check if there are more items
        # If we got exactly limit items, there are no more
        # If we got limit + 1 items, there might be more
        has_more = len(transactions) > limit
        
        # Return only the requested limit
        return transactions[:limit], has_more
    
    def _apply_filters(self, query, filters: TransactionFilter):
        """Apply filters to query."""
        if filters.transaction_type:
            query = query.filter(Transaction.transaction_type == filters.transaction_type.value)
        
        if filters.product:
            query = query.filter(Transaction.product == filters.product.value)
        
        if filters.status:
            query = query.filter(Transaction.status == filters.status.value)
        
        if filters.currency:
            query = query.filter(Transaction.currency == filters.currency)
        
        if filters.start_date:
            query = query.filter(Transaction.created_at >= filters.start_date)
        
        if filters.end_date:
            query = query.filter(Transaction.created_at <= filters.end_date)
        
        if filters.min_amount is not None:
            query = query.filter(Transaction.amount >= filters.min_amount)
        
        if filters.max_amount is not None:
            query = query.filter(Transaction.amount <= filters.max_amount)
        
        if filters.search_query:
            # Full-text search on search_content field
            search_term = f"%{filters.search_query.lower()}%"
            query = query.filter(Transaction.search_content.ilike(search_term))
        
        if filters.metadata_filters:
            # Filter by JSON/JSONB metadata fields
            # Use PostgreSQL JSON ->> operator to extract text value
            for key, value in filters.metadata_filters.items():
                # For metadata filters, we need to:
                # 1. Extract the value using ->> operator (returns NULL if key doesn't exist)
                # 2. Check that the value is NOT NULL (ensures key exists)
                # 3. Compare the value exactly
                # This works for both JSON and JSONB types
                # PostgreSQL JSON/JSONB: ->> extracts value as text, returns NULL if key doesn't exist
                json_expr = Transaction.custom_metadata.op('->>')(key)
                # Only match if value is not NULL (key exists) AND value matches exactly
                query = query.filter(
                    and_(
                        json_expr.isnot(None),  # Key exists (value is not NULL)
                        json_expr == str(value)  # Value matches exactly
                    )
                )
        
        return query
    
    def update(self, transaction: Transaction, update_data: dict) -> Transaction:
        """Update a transaction."""
        for key, value in update_data.items():
            setattr(transaction, key, value)
        self.db.commit()
        self.db.refresh(transaction)
        return transaction
    
    def delete(self, transaction: Transaction) -> None:
        """Delete a transaction."""
        self.db.delete(transaction)
        self.db.commit()

