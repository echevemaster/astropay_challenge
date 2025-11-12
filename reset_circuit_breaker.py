#!/usr/bin/env python3
"""
Script to reset the Elasticsearch circuit breaker.

Usage:
    python reset_circuit_breaker.py

Or in Docker:
    docker-compose run --rm api python reset_circuit_breaker.py
"""
import os
import sys
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    try:
        import httpx
        HAS_REQUESTS = False
        HAS_HTTPX = True
    except ImportError:
        HAS_REQUESTS = False
        HAS_HTTPX = False

from app.middleware.circuit_breaker import get_elasticsearch_breaker, get_redis_breaker, get_kafka_breaker
from app.services.search_service import SearchService

# Detect if we are in Docker
if os.getenv("DOCKER_CONTAINER"):
    ELASTICSEARCH_URL = os.getenv("ELASTICSEARCH_URL", "http://elasticsearch:9200")
else:
    ELASTICSEARCH_URL = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")


def check_elasticsearch():
    """Checks if Elasticsearch is available."""
    try:
        if HAS_REQUESTS:
            response = requests.get(f"{ELASTICSEARCH_URL}/_cluster/health", timeout=5)
            if response.status_code == 200:
                health = response.json()
                return health.get("status") in ["green", "yellow"]
        elif HAS_HTTPX:
            response = httpx.get(f"{ELASTICSEARCH_URL}/_cluster/health", timeout=5)
            if response.status_code == 200:
                health = response.json()
                return health.get("status") in ["green", "yellow"]
        else:
            # Fallback: usar el SearchService directamente
            try:
                search_service = SearchService()
                return search_service.enabled
            except:
                return False
        return False
    except Exception as e:
        print(f"❌ Error checking Elasticsearch: {e}")
        return False


def reset_circuit_breakers():
    """Resets the circuit breakers."""
    print("🔄 Resetting circuit breakers...")
    print("-" * 60)
    
    # Elasticsearch
    print("🔍 Checking Elasticsearch...")
    es_available = check_elasticsearch()
    if es_available:
        print("✅ Elasticsearch is available")
    else:
        print("❌ Elasticsearch is NOT available")
        print("   Make sure Elasticsearch is running:")
        print("   docker-compose up -d elasticsearch")
    
    print()
    
    # Reset circuit breakers
    es_breaker = get_elasticsearch_breaker()
    redis_breaker = get_redis_breaker()
    kafka_breaker = get_kafka_breaker()
    
    print("📊 Current circuit breaker status:")
    print()
    
    # Elasticsearch
    es_state = es_breaker.get_state()
    print(f"Elasticsearch:")
    print(f"   Status: {es_state['state']}")
    print(f"   Failures: {es_state['failure_count']}/{es_state['threshold']}")
    print(f"   Last failure: {es_state['last_failure_time'] or 'N/A'}")
    
    if es_state['state'] == 'open':
        if es_available:
            print("   🔄 Resetting circuit breaker...")
            es_breaker.reset()
            print("   ✅ Circuit breaker reset")
            
            # Test connection
            try:
                search_service = SearchService()
                if search_service.enabled:
                    print("   ✅ Elasticsearch connection verified")
                else:
                    print("   ⚠️  Elasticsearch service is not enabled")
            except Exception as e:
                print(f"   ⚠️  Error verifying connection: {e}")
        else:
            print("   ⚠️  Cannot reset: Elasticsearch is not available")
    else:
        print("   ✅ Circuit breaker is closed (functioning)")
    
    print()
    
    # Redis
    redis_state = redis_breaker.get_state()
    print(f"Redis:")
    print(f"   Status: {redis_state['state']}")
    if redis_state['state'] == 'open':
        print("   🔄 Resetting circuit breaker...")
        redis_breaker.reset()
        print("   ✅ Circuit breaker reset")
    else:
        print("   ✅ Circuit breaker is closed (functioning)")
    
    print()
    
    # Kafka
    kafka_state = kafka_breaker.get_state()
    print(f"Kafka:")
    print(f"   Status: {kafka_state['state']}")
    if kafka_state['state'] == 'open':
        print("   🔄 Resetting circuit breaker...")
        kafka_breaker.reset()
        print("   ✅ Circuit breaker reset")
    else:
        print("   ✅ Circuit breaker is closed (functioning)")
    
    print()
    print("-" * 60)
    print("✅ Process completed")
    print()
    print("💡 If the circuit breaker opens again, check:")
    print("   1. That Elasticsearch is running: docker-compose ps elasticsearch")
    print("   2. That Elasticsearch is healthy: curl http://localhost:9200/_cluster/health")
    print("   3. That the Elasticsearch URL is correct in the configuration")


if __name__ == "__main__":
    reset_circuit_breakers()

