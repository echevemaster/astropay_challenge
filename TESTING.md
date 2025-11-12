# Testing Guide

This guide explains how to run and write tests for the application.

## Run Tests

### In Docker (Recommended)

```bash
# Use the automatic script
./run_tests_docker.sh

# With coverage
./run_tests_docker.sh --cov

# See more options
./run_tests_docker.sh --help
```

Or directly with docker-compose:

```bash
docker-compose --profile tests run --rm tests
```

> **📖 For more details on testing in Docker, see [DOCKER_TESTING.md](DOCKER_TESTING.md)**

### Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest
```

## Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures
├── test_utils_cursor.py     # Cursor utilities tests
├── test_repositories.py     # Repository tests
├── test_services.py         # Service tests
├── test_api_transactions.py # Transaction endpoint tests
├── test_api_auth.py         # Authentication endpoint tests
└── test_api_health.py       # Health check tests
```

## Run Tests

### All tests

```bash
pytest
```

### With coverage

```bash
pytest --cov=app --cov-report=html
```

### Specific tests

```bash
# A file
pytest tests/test_api_transactions.py

# A class
pytest tests/test_api_transactions.py::TestTransactionAPI

# A specific test
pytest tests/test_api_transactions.py::TestTransactionAPI::test_create_transaction
```

### With verbose output

```bash
pytest -v
```

### Unit tests only

```bash
pytest -m unit
```

### Integration tests only

```bash
pytest -m integration
```

## Write New Tests

### Test Structure

```python
import pytest

class TestMyFeature:
    """Test my feature."""
    
    def test_something(self, client, sample_transaction_data):
        """Test something."""
        response = client.post("/api/v1/transactions", json=sample_transaction_data)
        assert response.status_code == 201
```

### Available Fixtures

- `client`: FastAPI TestClient
- `db_session`: Database session
- `transaction_repository`: Repository instance
- `transaction_service`: Service instance
- `sample_transaction_data`: Example data for card transaction
- `sample_p2p_transaction_data`: Example data for P2P transaction
- `auth_token`: JWT token for testing
- `mock_cache_service`: Mock cache service
- `mock_search_service`: Mock search service
- `mock_event_service`: Mock event service

### Example: Endpoint Test

```python
def test_create_transaction(self, client, sample_transaction_data):
    """Test creating a transaction."""
    response = client.post(
        "/api/v1/transactions",
        json=sample_transaction_data
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == "test_user_123"
```

### Example: Service Test

```python
def test_create_transaction(self, transaction_service, sample_transaction_data):
    """Test creating a transaction."""
    transaction_create = TransactionCreate(**sample_transaction_data)
    result = transaction_service.create_transaction(transaction_create)
    
    assert result.user_id == "test_user_123"
```

## Test Coverage

Tests cover:

- ✅ Utilities (cursor pagination)
- ✅ Repositories (CRUD, filters, pagination)
- ✅ Services (business logic)
- ✅ API endpoints (transactions, auth, health)
- ✅ Pagination (offset and cursor)
- ✅ Filters (type, status, date, metadata)
- ✅ Search (free text)
- ✅ Authentication (JWT)

## CI/CD

Tests run automatically in GitHub Actions on each push and pull request.

## Notes

- Tests use in-memory SQLite for the database
- External services (Redis, Elasticsearch, Kafka) are mocked
- Each test has its own clean database session
- Fixtures are recreated for each test
