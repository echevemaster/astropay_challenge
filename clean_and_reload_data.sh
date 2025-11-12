#!/bin/bash

# Script to clean and reload test data

echo "🧹 Cleaning and reloading test data..."
echo ""

# Verify Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Verify services are running
echo "🔍 Verifying services..."
if ! docker-compose ps | grep -q "postgres.*Up"; then
    echo "⚠️  Services are not running."
    echo "   Starting necessary services..."
    docker-compose up -d postgres redis elasticsearch kafka zookeeper api
    echo "   Waiting for services to be ready..."
    sleep 15
fi

echo "✅ Services verified"
echo ""

# Step 1: Clean data
echo "🧹 Step 1: Cleaning existing data..."
echo ""
docker-compose --profile clean run --rm clean_data

if [ $? -ne 0 ]; then
    echo "❌ Error cleaning data"
    exit 1
fi

echo ""
echo "✅ Data cleaned successfully"
echo ""

# Step 2: Load new data
echo "📦 Step 2: Loading new data..."
echo ""

# Rebuild image if necessary
echo "🔨 Checking dependencies..."
docker-compose build load_test_data
echo ""

# Run data loading service
docker-compose --profile test-data run --rm load_test_data

if [ $? -ne 0 ]; then
    echo "❌ Error loading data"
    exit 1
fi

echo ""
echo "✨ Process completed!"
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
