#!/bin/bash

# Script to clean data from the database and Elasticsearch using Docker

echo "🧹 Cleaning application data..."
echo ""

# Verify that Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Verify that services are running
echo "🔍 Verifying services..."
if ! docker-compose ps | grep -q "postgres.*Up"; then
    echo "⚠️  Services are not running."
    echo "   Starting necessary services..."
    docker-compose up -d postgres redis elasticsearch
    echo "   Waiting for services to be ready..."
    sleep 15
fi

echo "✅ Services verified"
echo ""

# Rebuild image if necessary
echo "🔨 Verifying dependencies..."
docker-compose build clean_data
echo ""

# Run cleaning service
echo "🧹 Cleaning data..."
docker-compose --profile clean run --rm clean_data

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Data cleaned successfully"
    echo ""
    echo "💡 To load new data, run:"
    echo "   ./load_test_data_docker.sh"
    echo "   or"
    echo "   ./clean_and_reload_data.sh"
else
    echo ""
    echo "❌ Error cleaning data"
    exit 1
fi

