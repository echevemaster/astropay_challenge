#!/bin/bash

# Complete diagnostic script for Kafka consumer

echo "🔍 Kafka Consumer Diagnostic"
echo "======================================"
echo ""

# 1. Verify consumer is running
echo "1️⃣ Checking consumer status..."
if docker-compose ps consumer | grep -q "Up"; then
    echo "   ✅ Consumer is running"
else
    echo "   ❌ Consumer is NOT running"
    echo "   💡 Start with: docker-compose up -d consumer"
    exit 1
fi
echo ""

# 2. Verify Kafka connection
echo "2️⃣ Verifying Kafka connection..."
if docker-compose exec -T kafka kafka-broker-api-versions --bootstrap-server localhost:9092 > /dev/null 2>&1; then
    echo "   ✅ Kafka is available"
else
    echo "   ❌ Kafka is NOT available"
    echo "   💡 Start with: docker-compose up -d kafka zookeeper"
    exit 1
fi
echo ""

# 3. Check topic status
echo "3️⃣ Checking topic status..."
TOPIC_INFO=$(docker-compose exec -T kafka kafka-topics --list --bootstrap-server localhost:9092 2>/dev/null | grep transactions || echo "")
if [ -z "$TOPIC_INFO" ]; then
    echo "   ⚠️  Topic 'transactions' does not exist"
    echo "   💡 Consumer should create it automatically on startup"
else
    echo "   ✅ Topic 'transactions' exists"
    
    # Check consumer group
    echo ""
    echo "   👥 Checking consumer group..."
    GROUP_INFO=$(docker-compose exec -T kafka kafka-consumer-groups --bootstrap-server localhost:9092 --group transaction_indexer --describe 2>/dev/null || echo "")
    if [ -z "$GROUP_INFO" ] || echo "$GROUP_INFO" | grep -q "does not exist"; then
        echo "   ⚠️  Consumer group 'transaction_indexer' does not exist or has no activity"
        echo "   💡 Consumer should register automatically on startup"
    else
        echo "   ✅ Consumer group active"
        echo "$GROUP_INFO" | head -10
    fi
fi
echo ""

# 4. Check recent consumer logs
echo "4️⃣ Recent consumer logs..."
echo "   (Last 20 lines)"
docker-compose logs --tail=20 consumer | tail -20
echo ""

# 5. Check for errors in logs
echo "5️⃣ Searching for errors in logs..."
ERRORS=$(docker-compose logs consumer 2>&1 | grep -i "error\|exception\|failed" | tail -5)
if [ -z "$ERRORS" ]; then
    echo "   ✅ No recent errors found"
else
    echo "   ⚠️  Errors found:"
    echo "$ERRORS"
fi
echo ""

# 6. Check Elasticsearch
echo "6️⃣ Checking Elasticsearch..."
if curl -s http://localhost:9200/_cluster/health > /dev/null 2>&1; then
    ES_STATUS=$(curl -s http://localhost:9200/_cluster/health | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
    echo "   ✅ Elasticsearch is available (status: $ES_STATUS)"
else
    echo "   ⚠️  Elasticsearch is NOT available"
    echo "   💡 Start: docker-compose up -d elasticsearch"
fi
echo ""

# 7. Summary and recommendations
echo "📋 Summary and Recommendations:"
echo "=============================="
echo ""
echo "If messages are not being consumed:"
echo "  1. Reset circuit breaker:"
echo "     docker-compose run --rm api python reset_circuit_breaker.py"
echo ""
echo "  2. Restart consumer:"
echo "     docker-compose restart consumer"
echo ""
echo "  3. View logs in real time:"
echo "     docker-compose logs -f consumer"
echo ""
echo "  4. Check topics and consumer groups:"
echo "     docker-compose exec kafka kafka-topics --list --bootstrap-server localhost:9092"
echo "     docker-compose exec kafka kafka-consumer-groups --bootstrap-server localhost:9092 --group transaction_indexer --describe"
echo ""
