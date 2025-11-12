#!/bin/bash

# Script to load test data using Docker

echo "🚀 Loading test data with Docker..."
echo ""

# Verify Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Verify services are running
echo "🔍 Verifying services..."
if ! docker-compose ps | grep -q "api.*Up"; then
    echo "⚠️  The 'api' service is not running."
    echo "   Starting necessary services..."
    docker-compose up -d postgres redis elasticsearch kafka zookeeper api
    echo "   Waiting for API to be ready..."
    sleep 10
fi

echo "✅ Services verified"
echo ""

# Rebuild image if necessary (to include new dependencies)
echo "🔨 Checking dependencies..."
docker-compose build load_test_data
echo ""

# Run data loading service
echo "📦 Generating and loading 1000 transactions..."
echo ""

docker-compose --profile test-data run --rm load_test_data

echo ""
echo "✨ Done! Test data has been loaded."
echo ""
echo "💡 Query examples:"
echo ""
echo "   # View all transactions"
echo "   curl \"http://localhost:8000/api/v1/transactions?user_id=test_user_123\""
echo ""
echo "   # Search by merchant"
echo "   curl \"http://localhost:8000/api/v1/transactions?user_id=test_user_123&search_query=Starbucks\""
echo ""
echo "   # Filter by product"
echo "   curl \"http://localhost:8000/api/v1/transactions?user_id=test_user_123&product=Card\""
echo ""
echo "   # Search by peer name"
echo "   curl \"http://localhost:8000/api/v1/transactions?user_id=test_user_123&search_query=John\""
echo ""
