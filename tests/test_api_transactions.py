"""Tests for transaction API endpoints."""
import pytest
from datetime import datetime


class TestTransactionAPI:
    """Test transaction API endpoints."""
    
    def test_create_transaction(self, client, sample_transaction_data):
        """Test creating a transaction via API."""
        response = client.post(
            "/api/v1/transactions",
            json=sample_transaction_data
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == "test_user_123"
        assert data["transaction_type"] == "card"
        assert data["amount"] == 150.00
        assert data["metadata"]["merchant_name"] == "Starbucks"
    
    def test_create_transaction_with_jwt(self, client, auth_token, sample_transaction_data):
        """Test creating transaction with JWT authentication."""
        response = client.post(
            "/api/v1/transactions",
            json=sample_transaction_data,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 201
    
    def test_get_transactions_without_auth(self, client, sample_transaction_data):
        """Test getting transactions without JWT (development mode)."""
        # Create a transaction first
        client.post("/api/v1/transactions", json=sample_transaction_data)
        
        response = client.get(
            "/api/v1/transactions",
            params={"user_id": "test_user_123"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) > 0
    
    def test_get_transactions_with_jwt(self, client, auth_token, sample_transaction_data):
        """Test getting transactions with JWT."""
        # Create a transaction first
        client.post(
            "/api/v1/transactions",
            json=sample_transaction_data,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        response = client.get(
            "/api/v1/transactions",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
    
    def test_get_transactions_missing_user_id(self, client):
        """Test getting transactions without user_id."""
        response = client.get("/api/v1/transactions")
        
        assert response.status_code == 400
        assert "user_id is required" in response.json()["detail"]
    
    def test_get_transactions_with_filters(self, client, sample_transaction_data):
        """Test getting transactions with filters."""
        # Create transactions
        client.post("/api/v1/transactions", json=sample_transaction_data)
        
        response = client.get(
            "/api/v1/transactions",
            params={
                "user_id": "test_user_123",
                "transaction_type": "card",
                "status": "completed"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert all(item["transaction_type"] == "card" for item in data["items"])
        assert all(item["status"] == "completed" for item in data["items"])
    
    def test_get_transactions_with_date_filter(self, client, sample_transaction_data):
        """Test getting transactions with date filters."""
        client.post("/api/v1/transactions", json=sample_transaction_data)
        
        start_date = datetime(2024, 1, 1).isoformat() + "Z"
        end_date = datetime(2024, 12, 31).isoformat() + "Z"
        
        response = client.get(
            "/api/v1/transactions",
            params={
                "user_id": "test_user_123",
                "start_date": start_date,
                "end_date": end_date
            }
        )
        
        assert response.status_code == 200
    
    def test_get_transactions_with_metadata_filter(self, client, sample_p2p_transaction_data):
        """Test getting transactions with metadata filters."""
        client.post("/api/v1/transactions", json=sample_p2p_transaction_data)
        
        response = client.get(
            "/api/v1/transactions",
            params={
                "user_id": "test_user_123",
                "transaction_type": "p2p",
                "direction": "sent"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        if data["items"]:
            assert data["items"][0]["metadata"]["direction"] == "sent"
    
    def test_get_transactions_with_search_query(self, client, sample_transaction_data):
        """Test getting transactions with search query."""
        client.post("/api/v1/transactions", json=sample_transaction_data)
        
        response = client.get(
            "/api/v1/transactions",
            params={
                "user_id": "test_user_123",
                "search_query": "Starbucks"
            }
        )
        
        assert response.status_code == 200
    
    def test_get_transactions_offset_pagination(self, client, sample_transaction_data):
        """Test offset-based pagination."""
        # Create multiple transactions
        for i in range(5):
            data = sample_transaction_data.copy()
            data["amount"] = float(100 + i * 10)
            client.post("/api/v1/transactions", json=data)
        
        response = client.get(
            "/api/v1/transactions",
            params={
                "user_id": "test_user_123",
                "page": 1,
                "page_size": 2
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["page"] == 1
        assert data["page_size"] == 2
        assert "total" in data
        assert "total_pages" in data
    
    def test_get_transaction_by_id(self, client, sample_transaction_data):
        """Test getting a single transaction by ID."""
        # Create transaction
        create_response = client.post("/api/v1/transactions", json=sample_transaction_data)
        transaction_id = create_response.json()["id"]
        
        # Get transaction
        response = client.get(f"/api/v1/transactions/{transaction_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == transaction_id
        assert data["user_id"] == "test_user_123"
    
    def test_get_transaction_invalid_id(self, client):
        """Test getting transaction with invalid ID format."""
        response = client.get("/api/v1/transactions/invalid-id")
        
        assert response.status_code == 400
        assert "Invalid transaction ID format" in response.json()["detail"]
    
    def test_get_transaction_not_found(self, client):
        """Test getting non-existent transaction."""
        from uuid import uuid4
        response = client.get(f"/api/v1/transactions/{uuid4()}")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_card_payment_filter(self, client, sample_transaction_data):
        """Test filtering card payments."""
        client.post("/api/v1/transactions", json=sample_transaction_data)
        
        response = client.get(
            "/api/v1/transactions",
            params={
                "user_id": "test_user_123",
                "transaction_type": "card"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert all(item["transaction_type"] == "card" for item in data["items"])
    
    def test_card_payment_by_last_four(self, client, sample_transaction_data):
        """Test filtering by card last four digits."""
        client.post("/api/v1/transactions", json=sample_transaction_data)
        
        response = client.get(
            "/api/v1/transactions",
            params={
                "user_id": "test_user_123",
                "transaction_type": "card",
                "card_last_four": "5678"
            }
        )
        
        assert response.status_code == 200
    
    def test_p2p_direction_filter(self, client, sample_p2p_transaction_data):
        """Test filtering P2P by direction."""
        client.post("/api/v1/transactions", json=sample_p2p_transaction_data)
        
        response = client.get(
            "/api/v1/transactions",
            params={
                "user_id": "test_user_123",
                "transaction_type": "p2p",
                "direction": "sent"
            }
        )
        
        assert response.status_code == 200

