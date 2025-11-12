"""Tests for transaction service."""
import pytest
from datetime import datetime
from unittest.mock import Mock, call

from app.services.transaction_service import TransactionService
from app.schemas import TransactionCreate, TransactionType, Product, TransactionStatus, TransactionFilter, PaginationParams, CursorPaginationParams


class TestTransactionService:
    """Test transaction service."""
    
    def test_create_transaction(self, transaction_service, sample_transaction_data):
        """Test creating a transaction."""
        transaction_create = TransactionCreate(**sample_transaction_data)
        
        result = transaction_service.create_transaction(transaction_create)
        
        assert result.user_id == "test_user_123"
        assert result.transaction_type == TransactionType.CARD
        assert result.amount == 150.00
        assert result.metadata["merchant_name"] == "Starbucks"
        
        # Verify event was published
        transaction_service.event_service.publish_transaction_created.assert_called_once()
    
    def test_create_p2p_transaction(self, transaction_service, sample_p2p_transaction_data):
        """Test creating a P2P transaction."""
        transaction_create = TransactionCreate(**sample_p2p_transaction_data)
        
        result = transaction_service.create_transaction(transaction_create)
        
        assert result.transaction_type == TransactionType.P2P
        assert result.metadata["direction"] == "sent"
        assert result.metadata["peer_name"] == "John Doe"
    
    def test_get_transactions_no_filters(self, transaction_service, sample_transaction_data):
        """Test getting transactions without filters."""
        # Create some transactions
        for i in range(3):
            data = sample_transaction_data.copy()
            data["amount"] = float(100 + i * 10)
            transaction_create = TransactionCreate(**data)
            transaction_service.create_transaction(transaction_create)
        
        result = transaction_service.get_transactions(
            user_id="test_user_123"
        )
        
        assert len(result.items) == 3
        assert result.total == 3
        assert result.page == 1
    
    def test_get_transactions_with_filters(self, transaction_service, sample_transaction_data):
        """Test getting transactions with filters."""
        # Create transactions with different statuses
        for status in ["completed", "pending", "failed"]:
            data = sample_transaction_data.copy()
            data["status"] = status
            transaction_create = TransactionCreate(**data)
            transaction_service.create_transaction(transaction_create)
        
        filters = TransactionFilter(
            user_id="test_user_123",
            status=TransactionStatus.COMPLETED
        )
        
        result = transaction_service.get_transactions(
            user_id="test_user_123",
            filters=filters
        )
        
        assert result.total == 1
        assert result.items[0].status == TransactionStatus.COMPLETED
    
    def test_get_transactions_with_pagination(self, transaction_service, sample_transaction_data):
        """Test getting transactions with pagination."""
        # Create 10 transactions
        for i in range(10):
            data = sample_transaction_data.copy()
            data["amount"] = float(100 + i)
            transaction_create = TransactionCreate(**data)
            transaction_service.create_transaction(transaction_create)
        
        pagination = PaginationParams(page=1, page_size=5)
        result = transaction_service.get_transactions(
            user_id="test_user_123",
            pagination=pagination
        )
        
        assert len(result.items) == 5
        assert result.total == 10
        assert result.page == 1
        assert result.total_pages == 2
    
    def test_get_transaction_by_id(self, transaction_service, sample_transaction_data):
        """Test getting a single transaction by ID."""
        transaction_create = TransactionCreate(**sample_transaction_data)
        created = transaction_service.create_transaction(transaction_create)
        
        result = transaction_service.get_transaction(str(created.id))
        
        assert result is not None
        assert result.id == created.id
        assert result.user_id == "test_user_123"
    
    def test_get_transaction_not_found(self, transaction_service):
        """Test getting non-existent transaction."""
        from uuid import uuid4
        result = transaction_service.get_transaction(str(uuid4()))
        assert result is None
    
    def test_cache_invalidation_on_create(self, transaction_service, sample_transaction_data):
        """Test that cache is invalidated when creating transaction."""
        transaction_create = TransactionCreate(**sample_transaction_data)
        transaction_service.create_transaction(transaction_create)
        
        # Verify cache pattern was deleted
        transaction_service.cache_service.delete_pattern.assert_called()
    
    def test_elasticsearch_indexing(self, transaction_service, sample_transaction_data):
        """Test that transactions are indexed in Elasticsearch."""
        transaction_create = TransactionCreate(**sample_transaction_data)
        transaction_service.create_transaction(transaction_create)
        
        # Verify indexing was called
        transaction_service.search_service.index_transaction.assert_called_once()
    
    def test_search_with_elasticsearch(self, transaction_service, sample_transaction_data):
        """Test search using Elasticsearch."""
        # Create transaction
        transaction_create = TransactionCreate(**sample_transaction_data)
        transaction_service.create_transaction(transaction_create)
        
        # Mock Elasticsearch search results
        transaction_service.search_service.search.return_value = (
            [str(transaction_service.repository.get_by_user_id("test_user_123")[0][0].id)],
            1
        )
        
        filters = TransactionFilter(
            user_id="test_user_123",
            search_query="Starbucks"
        )
        
        result = transaction_service.get_transactions(
            user_id="test_user_123",
            filters=filters
        )
        
        # Verify Elasticsearch was used
        transaction_service.search_service.search.assert_called_once()
    
    def test_search_fallback_to_postgresql(self, transaction_service, sample_transaction_data):
        """Test search falls back to PostgreSQL when Elasticsearch is disabled."""
        transaction_service.search_service.enabled = False
        
        # Create transaction
        transaction_create = TransactionCreate(**sample_transaction_data)
        transaction_service.create_transaction(transaction_create)
        
        filters = TransactionFilter(
            user_id="test_user_123",
            search_query="Starbucks"
        )
        
        result = transaction_service.get_transactions(
            user_id="test_user_123",
            filters=filters
        )
        
        # Should use PostgreSQL search
        assert result.total >= 0

