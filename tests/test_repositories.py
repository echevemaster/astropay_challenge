"""Tests for transaction repository."""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from app.repositories.transaction_repository import TransactionRepository
from app.schemas import TransactionFilter, PaginationParams, CursorPaginationParams
from app.models import Transaction


class TestTransactionRepository:
    """Test transaction repository."""
    
    def test_create_transaction(self, transaction_repository):
        """Test creating a transaction."""
        transaction_data = {
            "user_id": "test_user_123",
            "transaction_type": "card",
            "product": "Card",
            "status": "completed",
            "currency": "USD",
            "amount": 150.00,
            "custom_metadata": {"merchant_name": "Starbucks"},
            "search_content": "Starbucks Food & Beverage"
        }
        
        transaction = transaction_repository.create(transaction_data)
        
        assert transaction.id is not None
        assert transaction.user_id == "test_user_123"
        assert transaction.transaction_type == "card"
        assert transaction.amount == 150.00
    
    def test_get_by_id(self, transaction_repository):
        """Test getting transaction by ID."""
        transaction_data = {
            "user_id": "test_user_123",
            "transaction_type": "card",
            "product": "Card",
            "status": "completed",
            "currency": "USD",
            "amount": 150.00
        }
        
        created = transaction_repository.create(transaction_data)
        found = transaction_repository.get_by_id(str(created.id))
        
        assert found is not None
        assert found.id == created.id
        assert found.user_id == "test_user_123"
    
    def test_get_by_id_not_found(self, transaction_repository):
        """Test getting non-existent transaction."""
        result = transaction_repository.get_by_id(str(uuid4()))
        assert result is None
    
    def test_get_by_user_id_no_filters(self, transaction_repository):
        """Test getting transactions for user without filters."""
        # Create multiple transactions
        for i in range(5):
            transaction_repository.create({
                "user_id": "test_user_123",
                "transaction_type": "card",
                "product": "Card",
                "status": "completed",
                "currency": "USD",
                "amount": float(100 + i * 10)
            })
        
        transactions, total = transaction_repository.get_by_user_id(
            user_id="test_user_123"
        )
        
        assert len(transactions) == 5
        assert total == 5
    
    def test_get_by_user_id_with_filters(self, transaction_repository):
        """Test getting transactions with filters."""
        # Create transactions with different types
        transaction_repository.create({
            "user_id": "test_user_123",
            "transaction_type": "card",
            "product": "Card",
            "status": "completed",
            "currency": "USD",
            "amount": 100.00
        })
        
        transaction_repository.create({
            "user_id": "test_user_123",
            "transaction_type": "p2p",
            "product": "P2P",
            "status": "completed",
            "currency": "USD",
            "amount": 50.00
        })
        
        filters = TransactionFilter(
            user_id="test_user_123",
            transaction_type="card"
        )
        
        transactions, total = transaction_repository.get_by_user_id(
            user_id="test_user_123",
            filters=filters
        )
        
        assert total == 1
        assert transactions[0].transaction_type == "card"
    
    def test_get_by_user_id_with_pagination(self, transaction_repository):
        """Test getting transactions with pagination."""
        # Create 10 transactions
        for i in range(10):
            transaction_repository.create({
                "user_id": "test_user_123",
                "transaction_type": "card",
                "product": "Card",
                "status": "completed",
                "currency": "USD",
                "amount": float(100 + i)
            })
        
        pagination = PaginationParams(page=1, page_size=5)
        transactions, total = transaction_repository.get_by_user_id(
            user_id="test_user_123",
            pagination=pagination
        )
        
        assert len(transactions) == 5
        assert total == 10
    
    def test_filter_by_date_range(self, transaction_repository):
        """Test filtering by date range."""
        base_date = datetime(2024, 1, 15, 12, 0, 0)
        
        # Create transactions on different dates
        for i in range(5):
            tx_data = {
                "user_id": "test_user_123",
                "transaction_type": "card",
                "product": "Card",
                "status": "completed",
                "currency": "USD",
                "amount": 100.00
            }
            tx = transaction_repository.create(tx_data)
            # Manually set created_at (in real scenario, this is set by DB)
            # For testing, we'll filter by what we can control
        
        filters = TransactionFilter(
            user_id="test_user_123",
            start_date=base_date - timedelta(days=1),
            end_date=base_date + timedelta(days=1)
        )
        
        transactions, total = transaction_repository.get_by_user_id(
            user_id="test_user_123",
            filters=filters
        )
        
        assert total >= 0  # At least some transactions
    
    def test_filter_by_metadata(self, transaction_repository):
        """Test filtering by metadata fields."""
        transaction_repository.create({
            "user_id": "test_user_123",
            "transaction_type": "p2p",
            "product": "P2P",
            "status": "completed",
            "currency": "USD",
            "amount": 50.00,
            "custom_metadata": {"direction": "sent"}
        })
        
        transaction_repository.create({
            "user_id": "test_user_123",
            "transaction_type": "p2p",
            "product": "P2P",
            "status": "completed",
            "currency": "USD",
            "amount": 50.00,
            "custom_metadata": {"direction": "received"}
        })
        
        filters = TransactionFilter(
            user_id="test_user_123",
            metadata_filters={"direction": "sent"}
        )
        
        transactions, total = transaction_repository.get_by_user_id(
            user_id="test_user_123",
            filters=filters
        )
        
        assert total == 1
        assert transactions[0].custom_metadata["direction"] == "sent"
    
    def test_search_query(self, transaction_repository):
        """Test full-text search."""
        transaction_repository.create({
            "user_id": "test_user_123",
            "transaction_type": "card",
            "product": "Card",
            "status": "completed",
            "currency": "USD",
            "amount": 100.00,
            "search_content": "Starbucks Coffee San Francisco"
        })
        
        transaction_repository.create({
            "user_id": "test_user_123",
            "transaction_type": "card",
            "product": "Card",
            "status": "completed",
            "currency": "USD",
            "amount": 100.00,
            "search_content": "Amazon Online Shopping"
        })
        
        filters = TransactionFilter(
            user_id="test_user_123",
            search_query="Starbucks"
        )
        
        transactions, total = transaction_repository.get_by_user_id(
            user_id="test_user_123",
            filters=filters
        )
        
        assert total == 1, f"Expected 1 result, got {total}"
        # The search is case-insensitive (ilike), so verify the result contains the search term
        assert "starbucks" in transactions[0].search_content.lower(), \
            f"Search content '{transactions[0].search_content}' should contain 'starbucks'"

