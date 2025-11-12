# Run Tests in Docker

This guide explains how to run the application tests using Docker.

## Option 1: Automatic Script (Recommended) ⭐

```bash
# Run all tests
./run_tests_docker.sh

# With code coverage
./run_tests_docker.sh --cov

# Verbose mode
./run_tests_docker.sh --verbose

# Run a specific file
./run_tests_docker.sh --file tests/test_api_transactions.py

# Run tests with a specific marker
./run_tests_docker.sh --marker unit
```

## Option 2: Docker Compose Directly

### Run all tests

```bash
docker-compose --profile tests run --rm tests
```

### With coverage

```bash
docker-compose --profile tests run --rm tests pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=html
```

### Specific tests

```bash
# A specific file
docker-compose --profile tests run --rm tests pytest tests/test_api_transactions.py

# A specific class
docker-compose --profile tests run --rm tests pytest tests/test_api_transactions.py::TestTransactionAPI

# A specific test
docker-compose --profile tests run --rm tests pytest tests/test_api_transactions.py::TestTransactionAPI::test_create_transaction
```

### With additional options

```bash
# Verbose mode
docker-compose --profile tests run --rm tests pytest tests/ -v

# With markers
docker-compose --profile tests run --rm tests pytest tests/ -m unit

# Show errors only
docker-compose --profile tests run --rm tests pytest tests/ -v --tb=short
```

## Option 3: Run inside the API container

If the API is already running, you can run tests inside its container:

```bash
# Run all tests
docker-compose exec api pytest tests/

# With coverage
docker-compose exec api pytest tests/ --cov=app --cov-report=html
```

## Prerequisites

1. **Docker and Docker Compose installed**
2. **Infrastructure services (optional for unit tests)**

Unit tests use in-memory SQLite and mocks for external services, so they don't need infrastructure services running. However, if you want to run integration tests, you'll need:

```bash
docker-compose up -d postgres redis elasticsearch kafka zookeeper
```

## Test Structure

Tests are organized in:

```
tests/
├── conftest.py              # Shared fixtures
├── test_utils_cursor.py     # Utility tests
├── test_repositories.py     # Repository tests
├── test_services.py         # Service tests
├── test_api_transactions.py # Transaction API tests
├── test_api_auth.py         # Authentication tests
└── test_api_health.py       # Health check tests
```

## Script Options

The `run_tests_docker.sh` script accepts the following options:

- `--cov`: Run with code coverage
- `--verbose` or `-v`: Verbose mode
- `--file <file>`: Run a specific test file
- `--marker <tag>` or `-m <tag>`: Run tests with a specific marker
- `--help` or `-h`: Show help

## Usage Examples

### Run all tests

```bash
./run_tests_docker.sh
```

### With coverage and HTML report

```bash
./run_tests_docker.sh --cov
```

The HTML report will be generated in `htmlcov/index.html`

### Run only API tests

```bash
./run_tests_docker.sh --file tests/test_api_transactions.py
```

### Run only unit tests

```bash
./run_tests_docker.sh --marker unit
```

### Run only integration tests

```bash
./run_tests_docker.sh --marker integration
```

### Run a specific test

```bash
docker-compose --profile tests run --rm tests pytest tests/test_api_transactions.py::TestTransactionAPI::test_create_transaction -v
```

## View Coverage Results

After running with `--cov`, you can view the HTML report:

```bash
# If you're in Docker, copy the report
docker-compose --profile tests run --rm tests pytest tests/ --cov=app --cov-report=html
# Then open htmlcov/index.html in your browser
```

Or if you ran locally:

```bash
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## Troubleshooting

### Error: "No module named 'pytest'"

Make sure dependencies are installed. Rebuild the image:

```bash
docker-compose build tests
```

### Error: "Database connection failed"

Unit tests use in-memory SQLite, they don't need PostgreSQL. If you see this error, verify that `conftest.py` is configured correctly.

### Tests very slow

Tests should run quickly since they use mocks. If they're slow, verify:
- You're not connecting to real external services
- Mocks are configured correctly

### Clean up after tests

```bash
# Clean test containers and volumes
docker-compose --profile tests down -v
```

## CI/CD

Tests can also be run in CI/CD. See `.github/workflows/tests.yml` for GitHub Actions configuration.

## Notes

- Tests use in-memory SQLite for the database
- External services (Redis, Elasticsearch, Kafka) are mocked
- Each test has its own clean database session
- Fixtures are recreated for each test
- The test service doesn't need other services to be running
