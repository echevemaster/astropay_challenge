#!/bin/bash

# Script to run tests in Docker

set -e

echo "🧪 Running tests in Docker..."
echo ""

# Verify that Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Verify that docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose is not installed."
    exit 1
fi

# Available options
RUN_COV=false
RUN_VERBOSE=false
RUN_SPECIFIC=""
RUN_MARKER=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --cov)
            RUN_COV=true
            shift
            ;;
        --verbose|-v)
            RUN_VERBOSE=true
            shift
            ;;
        --file)
            RUN_SPECIFIC="$2"
            shift 2
            ;;
        --marker|-m)
            RUN_MARKER="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: ./run_tests_docker.sh [options]"
            echo ""
            echo "Options:"
            echo "  --cov              Run with code coverage"
            echo "  --verbose, -v      Run in verbose mode"
            echo "  --file <file>      Run a specific test file"
            echo "  --marker, -m <tag> Run tests with a specific marker"
            echo "  --help, -h         Show this help"
            echo ""
            echo "Examples:"
            echo "  ./run_tests_docker.sh"
            echo "  ./run_tests_docker.sh --cov"
            echo "  ./run_tests_docker.sh --file tests/test_api_transactions.py"
            echo "  ./run_tests_docker.sh --marker unit"
            exit 0
            ;;
        *)
            echo "❌ Unknown option: $1"
            echo "Use --help to see available options"
            exit 1
            ;;
    esac
done

# Build pytest command
PYTEST_CMD="pytest"

if [ "$RUN_VERBOSE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -v"
fi

if [ "$RUN_COV" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --cov=app --cov-report=term-missing --cov-report=html"
fi

if [ -n "$RUN_SPECIFIC" ]; then
    PYTEST_CMD="$PYTEST_CMD $RUN_SPECIFIC"
else
    PYTEST_CMD="$PYTEST_CMD tests/"
fi

if [ -n "$RUN_MARKER" ]; then
    PYTEST_CMD="$PYTEST_CMD -m $RUN_MARKER"
fi

echo "📋 Command: $PYTEST_CMD"
echo ""

# Run tests
docker-compose --profile tests run --rm tests $PYTEST_CMD

echo ""
echo "✅ Tests completed"

