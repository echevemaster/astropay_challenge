"""
Examples of using the Activity Feed API.

This script shows how to use the API to create and query transactions.
Run after starting the application with: python examples.py
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000/api/v1"


def create_card_transaction():
    """Example: Create a card payment transaction."""
    url = f"{BASE_URL}/transactions"
    data = {
        "user_id": "user123",
        "transaction_type": "card",
        "product": "Card",
        "status": "completed",
        "currency": "USD",
        "amount": 150.00,
        "metadata": {
            "merchant_name": "Starbucks",
            "merchant_category": "Food & Beverage",
            "card_last_four": "5678",
            "location": "San Francisco, CA"
        }
    }
    response = requests.post(url, json=data)
    print(f"✅ Card transaction created: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    return response.json()


def create_p2p_transaction():
    """Example: Create a P2P transaction."""
    url = f"{BASE_URL}/transactions"
    data = {
        "user_id": "user123",
        "transaction_type": "p2p",
        "product": "P2P",
        "status": "completed",
        "currency": "USD",
        "amount": 50.00,
        "metadata": {
            "peer_name": "John Doe",
            "peer_email": "john@example.com",
            "direction": "sent"
        }
    }
    response = requests.post(url, json=data)
    print(f"✅ P2P transaction created: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    return response.json()


def get_transactions_with_filters():
    """Example: Get transactions with filters."""
    url = f"{BASE_URL}/transactions"
    params = {
        "user_id": "user123",
        "product": "Card",
        "status": "completed",
        "page": 1,
        "page_size": 20
    }
    response = requests.get(url, params=params)
    print(f"✅ Transactions retrieved: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    return response.json()


def search_transactions():
    """Example: Free-text search."""
    url = f"{BASE_URL}/transactions"
    params = {
        "user_id": "user123",
        "search_query": "Starbucks",
        "page": 1,
        "page_size": 20
    }
    response = requests.get(url, params=params)
    print(f"✅ Search performed: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    return response.json()


def get_health():
    """Example: Health check."""
    url = f"{BASE_URL}/health"
    response = requests.get(url)
    print(f"✅ Health check: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    return response.json()


if __name__ == "__main__":
    print("🚀 Activity Feed API Usage Examples\n")
    
    try:
        # Health check
        print("1. Health Check")
        print("-" * 50)
        get_health()
        print("\n")
        
        # Create transactions
        print("2. Create Card Transaction")
        print("-" * 50)
        create_card_transaction()
        print("\n")
        
        print("3. Create P2P Transaction")
        print("-" * 50)
        create_p2p_transaction()
        print("\n")
        
        # Query transactions
        print("4. Get Transactions with Filters")
        print("-" * 50)
        get_transactions_with_filters()
        print("\n")
        
        print("5. Free-Text Search")
        print("-" * 50)
        search_transactions()
        print("\n")
        
        print("✅ All examples executed successfully!")
        
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to API.")
        print("   Make sure the application is running at http://localhost:8000")
    except Exception as e:
        print(f"❌ Error: {e}")

