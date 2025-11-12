"""Pytest configuration and fixtures."""
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from typing import Generator
from unittest.mock import Mock, MagicMock

# Set SQLite database URL before importing app modules
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.main import app
from app.database import Base, get_db
from app.api.dependencies import (
    get_transaction_service,
    get_cache_service,
    get_search_service,
    get_event_service
)
from app.services.cache_service import CacheService
from app.services.search_service import SearchService
from app.services.event_service import EventService
from app.repositories.transaction_repository import TransactionRepository
from app.services.transaction_service import TransactionService


# In-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session() -> Generator:
    """Create a fresh database session for each test."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db(db_session):
    """Database session dependency override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    return override_get_db


@pytest.fixture(scope="function")
def mock_cache_service():
    """Mock cache service."""
    cache = Mock(spec=CacheService)
    cache.get = Mock(return_value=None)
    cache.set = Mock(return_value=True)
    cache.delete = Mock(return_value=True)
    cache.delete_pattern = Mock(return_value=True)
    return cache


@pytest.fixture(scope="function")
def mock_search_service():
    """Mock search service."""
    search = Mock(spec=SearchService)
    search.enabled = True
    search.index_transaction = Mock(return_value=True)
    search.search = Mock(return_value=([], 0))
    search.health_check = Mock(return_value=True)
    return search


@pytest.fixture(scope="function")
def mock_event_service():
    """Mock event service."""
    event = Mock(spec=EventService)
    event.enabled = True
    event.publish_transaction_created = Mock(return_value=True)
    event.publish_transaction_updated = Mock(return_value=True)
    event.health_check = Mock(return_value=True)
    return event


@pytest.fixture(scope="function")
def transaction_repository(db_session):
    """Transaction repository instance."""
    return TransactionRepository(db_session)


@pytest.fixture(scope="function")
def transaction_service(db_session, mock_cache_service, mock_search_service, mock_event_service):
    """Transaction service instance."""
    return TransactionService(
        db=db_session,
        cache_service=mock_cache_service,
        search_service=mock_search_service,
        event_service=mock_event_service
    )


@pytest.fixture(scope="function")
def client(db, mock_cache_service, mock_search_service, mock_event_service):
    """Test client with overridden dependencies."""
    def override_get_transaction_service():
        from app.services.transaction_service import TransactionService
        return TransactionService(
            db=next(db()),
            cache_service=mock_cache_service,
            search_service=mock_search_service,
            event_service=mock_event_service
        )
    
    app.dependency_overrides[get_db] = db
    app.dependency_overrides[get_transaction_service] = override_get_transaction_service
    app.dependency_overrides[get_cache_service] = lambda: mock_cache_service
    app.dependency_overrides[get_search_service] = lambda: mock_search_service
    app.dependency_overrides[get_event_service] = lambda: mock_event_service
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def sample_transaction_data():
    """Sample transaction data for testing."""
    return {
        "user_id": "test_user_123",
        "transaction_type": "card",
        "product": "Card",
        "status": "completed",
        "currency": "USD",
        "amount": 150.00,
        "metadata": {
            "merchant_name": "Starbucks",
            "merchant_category": "Food & Beverage",
            "card_last_four": "5678",
            "location": "San Francisco, CA"
        }
    }


@pytest.fixture
def sample_p2p_transaction_data():
    """Sample P2P transaction data for testing."""
    return {
        "user_id": "test_user_123",
        "transaction_type": "p2p",
        "product": "P2P",
        "status": "completed",
        "currency": "USD",
        "amount": 50.00,
        "metadata": {
            "peer_name": "John Doe",
            "peer_email": "john@example.com",
            "direction": "sent"
        }
    }


@pytest.fixture
def auth_token(client):
    """Get authentication token for testing."""
    response = client.post(
        "/api/v1/auth/token",
        json={"user_id": "test_user_123"}
    )
    assert response.status_code == 200, f"Failed to get token: {response.status_code} - {response.text}"
    data = response.json()
    assert "access_token" in data, f"Response missing access_token: {data}"
    return data["access_token"]

