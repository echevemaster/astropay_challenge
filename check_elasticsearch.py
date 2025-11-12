#!/usr/bin/env python3
"""
Script to check the status of Elasticsearch and if it's being used.
"""
import requests
import sys

BASE_URL = "http://localhost:8000/api/v1"

def check_elasticsearch_health():
    """Checks the status of Elasticsearch."""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            health = response.json()
            print("🔍 Elasticsearch status:")
            print(f"   Status: {health.get('elasticsearch', 'unknown')}")
            return health.get('elasticsearch') == 'healthy'
        else:
            print(f"❌ Error checking health: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error connecting to API: {e}")
        return False

def test_search_with_elasticsearch():
    """Tests a search and verifies if it uses Elasticsearch."""
    print("\n🧪 Testing search...")
    
    # Get token
    try:
        token_response = requests.post(
            f"{BASE_URL}/auth/token",
            json={"user_id": "test_user_123"},
            timeout=5
        )
        if token_response.status_code != 200:
            print("⚠️  Could not get token, using unauthenticated mode")
            token = None
        else:
            token = token_response.json()["access_token"]
            print("✅ Token obtained")
    except Exception as e:
        print(f"⚠️  Error getting token: {e}")
        token = None
    
    # Perform search
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    try:
        print("\n📊 Executing search: search_query=Starbucks")
        response = requests.get(
            f"{BASE_URL}/transactions",
            params={"search_query": "Starbucks", "page_size": 5},
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Search successful")
            print(f"   Total results: {data.get('total', 0)}")
            print(f"   Results on this page: {len(data.get('items', []))}")
            
            if data.get('total', 0) > 0:
                print("\n📝 First result:")
                first_item = data['items'][0]
                print(f"   ID: {first_item.get('id')}")
                print(f"   Type: {first_item.get('transaction_type')}")
                print(f"   Amount: {first_item.get('amount')} {first_item.get('currency')}")
                if first_item.get('metadata'):
                    print(f"   Metadata: {first_item['metadata']}")
        else:
            print(f"❌ Search error: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ Error performing search: {e}")

def main():
    print("🔍 Elasticsearch Checker")
    print("=" * 50)
    
    # Check health
    es_healthy = check_elasticsearch_health()
    
    if es_healthy:
        print("\n✅ Elasticsearch is available and healthy")
        print("   Searches should use Elasticsearch")
    else:
        print("\n⚠️  Elasticsearch is NOT available or not healthy")
        print("   Searches will use PostgreSQL as fallback")
    
    # Test search
    test_search_with_elasticsearch()
    
    print("\n" + "=" * 50)
    print("💡 To see detailed logs, check the API logs:")
    print("   docker-compose logs -f api | grep -i elasticsearch")

if __name__ == "__main__":
    main()

