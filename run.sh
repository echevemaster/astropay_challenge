#!/bin/bash

# Script to start the application

echo "🚀 Starting AstroPay Activity Feed API..."

# Verify if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Start services with Docker Compose
echo "📦 Starting services with Docker Compose..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 10

# Verify PostgreSQL connection
echo "🔍 Verifying PostgreSQL connection..."
until docker-compose exec -T postgres pg_isready -U astropay > /dev/null 2>&1; do
    echo "   Waiting for PostgreSQL..."
    sleep 2
done
echo "✅ PostgreSQL is ready"

# Run migrations
echo "🔄 Running database migrations..."
if command -v alembic &> /dev/null; then
    alembic upgrade head
else
    echo "⚠️  Alembic is not installed. Run: pip install -r requirements.txt"
fi

# Start the application
echo "🎯 Starting FastAPI application..."
echo "📚 Documentation available at: http://localhost:8000/docs"
echo "🏥 Health check available at: http://localhost:8000/api/v1/health"
echo ""
echo "Press Ctrl+C to stop the application"
echo ""

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

