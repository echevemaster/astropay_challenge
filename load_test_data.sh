#!/bin/bash

# Script to load test data into the API

echo "🚀 Loading test data..."
echo ""

# Verify that the API is available
echo "🔍 Verifying connection to API..."
if ! curl -s http://localhost:8000/api/v1/health > /dev/null; then
    echo "❌ API is not available at http://localhost:8000"
    echo "   Please start the API first:"
    echo "   docker-compose up api"
    echo "   or"
    echo "   uvicorn app.main:app --reload"
    exit 1
fi

echo "✅ API is available"
echo ""

# Run generation script
echo "📦 Generating and loading 1000 transactions..."
echo ""

python3 generate_test_data.py

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

