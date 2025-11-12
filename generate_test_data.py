"""
Script to generate synthetic test data.

Generates 1000 transactions with different types, products, statuses and metadata.
"""
import requests
import random
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any

# Detect if we are in Docker
# If API_URL is not defined, try to auto-detect
if os.getenv("API_URL"):
    BASE_URL = os.getenv("API_URL")
elif os.getenv("DOCKER_CONTAINER"):
    # If we are in Docker, use the service name
    BASE_URL = "http://api:8000/api/v1"
else:
    # Local development
    BASE_URL = "http://localhost:8000/api/v1"

# Synthetic data
MERCHANTS = [
    "Starbucks", "McDonald's", "Amazon", "Walmart", "Target", "Best Buy",
    "Home Depot", "Costco", "CVS Pharmacy", "Walgreens", "Whole Foods",
    "Trader Joe's", "Subway", "Pizza Hut", "Domino's", "Uber", "Lyft",
    "Netflix", "Spotify", "Apple Store", "Google Play", "Steam",
    "Nike", "Adidas", "Zara", "H&M", "Macy's", "Nordstrom", "Sephora",
    "Shell", "Exxon", "BP", "Chevron", "7-Eleven", "Circle K"
]

MERCHANT_CATEGORIES = [
    "Food & Beverage", "Retail", "Gas Station", "Entertainment",
    "Shopping", "Transportation", "Subscription", "Electronics",
    "Clothing", "Pharmacy", "Grocery", "Restaurant", "Coffee Shop"
]

LOCATIONS = [
    "New York, NY", "Los Angeles, CA", "Chicago, IL", "Houston, TX",
    "Phoenix, AZ", "Philadelphia, PA", "San Antonio, TX", "San Diego, CA",
    "Dallas, TX", "San Jose, CA", "Austin, TX", "Jacksonville, FL",
    "San Francisco, CA", "Columbus, OH", "Fort Worth, TX", "Charlotte, NC",
    "Seattle, WA", "Denver, CO", "Boston, MA", "Miami, FL"
]

PEER_NAMES = [
    "John Doe", "Jane Smith", "Bob Johnson", "Alice Williams",
    "Charlie Brown", "Diana Prince", "Edward Norton", "Fiona Apple",
    "George Washington", "Hannah Montana", "Isaac Newton", "Julia Roberts",
    "Kevin Hart", "Laura Palmer", "Michael Jackson", "Nancy Drew",
    "Oliver Twist", "Patricia Smith", "Quentin Tarantino", "Rachel Green"
]

PEER_EMAILS = [
    "john@example.com", "jane@example.com", "bob@example.com",
    "alice@example.com", "charlie@example.com", "diana@example.com",
    "edward@example.com", "fiona@example.com", "george@example.com",
    "hannah@example.com"
]

# Cryptocurrency types with their short codes for the currency field (max 10 characters)
CRYPTO_TYPES = ["Bitcoin", "Ethereum", "USDC", "USDT", "Litecoin", "Bitcoin Cash"]
# Mapping of full names to short codes for the currency field
CRYPTO_CURRENCY_CODES = {
    "Bitcoin": "BTC",
    "Ethereum": "ETH",
    "USDC": "USDC",
    "USDT": "USDT",
    "Litecoin": "LTC",
    "Bitcoin Cash": "BCH"
}

CURRENCIES = ["USD", "EUR", "GBP", "BRL", "MXN", "ARS"]

TRANSACTION_TYPES = ["card", "p2p", "crypto", "top_up", "withdrawal", "bill_payment", "earnings"]
PRODUCTS = ["Card", "P2P", "Crypto", "Earnings"]
STATUSES = ["completed", "pending", "failed", "cancelled"]

DIRECTIONS = ["sent", "received"]


def generate_card_transaction(user_id: str, date: datetime) -> Dict[str, Any]:
    """Generates a card transaction."""
    merchant = random.choice(MERCHANTS)
    category = random.choice(MERCHANT_CATEGORIES)
    location = random.choice(LOCATIONS)
    # Generate last 4 digits of card (always present for card transactions)
    card_last_four = f"{random.randint(1000, 9999):04d}"
    
    return {
        "user_id": user_id,
        "transaction_type": "card",
        "product": "Card",
        "status": random.choice(["completed", "pending", "failed"]),
        "currency": random.choice(CURRENCIES),
        "amount": round(random.uniform(5.00, 500.00), 2),
        "metadata": {
            "merchant_name": merchant,
            "merchant_category": category,
            "card_last_four": card_last_four,  # Always present for card transactions
            "location": location
        }
    }


def generate_p2p_transaction(user_id: str, date: datetime) -> Dict[str, Any]:
    """Generates a P2P transaction."""
    peer_name = random.choice(PEER_NAMES)
    peer_email = random.choice(PEER_EMAILS)
    direction = random.choice(DIRECTIONS)
    # Generate phone with correct format
    peer_phone = f"+1{random.randint(2000000000, 9999999999)}"
    
    return {
        "user_id": user_id,
        "transaction_type": "p2p",
        "product": "P2P",
        "status": random.choice(["completed", "pending", "failed"]),
        "currency": random.choice(CURRENCIES),
        "amount": round(random.uniform(10.00, 1000.00), 2),
        "metadata": {
            "peer_name": peer_name,  # Always present for P2P
            "peer_email": peer_email,  # Always present for P2P
            "peer_phone": peer_phone,  # Always present for P2P
            "direction": direction  # Always present for P2P: "sent" or "received"
        }
    }


def generate_crypto_transaction(user_id: str, date: datetime) -> Dict[str, Any]:
    """Generates a crypto transaction."""
    crypto_type = random.choice(CRYPTO_TYPES)
    # Use short code for currency (maximum 10 characters as per model)
    currency_code = CRYPTO_CURRENCY_CODES.get(crypto_type, crypto_type[:10])
    wallet_address = "0x" + "".join(random.choices("0123456789abcdef", k=40))
    transaction_hash = "0x" + "".join(random.choices("0123456789abcdef", k=64))
    
    return {
        "user_id": user_id,
        "transaction_type": "crypto",
        "product": "Crypto",
        "status": random.choice(["completed", "pending", "failed"]),
        "currency": currency_code,  # Use short code (BTC, ETH, etc.) to comply with String(10)
        "amount": round(random.uniform(0.001, 10.0), 6),
        "metadata": {
            "crypto_type": crypto_type,  # Full name in metadata for readability
            "wallet_address": wallet_address,  # Always present for crypto
            "transaction_hash": transaction_hash  # Always present for crypto
        }
    }


def generate_top_up_transaction(user_id: str, date: datetime) -> Dict[str, Any]:
    """Generates a top-up transaction."""
    payment_method = random.choice(["bank_transfer", "credit_card", "debit_card"])
    reference_number = f"REF{random.randint(100000, 999999)}"
    
    metadata = {
        "payment_method": payment_method,  # Always present for top_up
        "reference_number": reference_number  # Always present for top_up
    }
    
    # If payment method is card, add card_last_four
    if payment_method in ["credit_card", "debit_card"]:
        metadata["card_last_four"] = f"{random.randint(1000, 9999):04d}"
    
    return {
        "user_id": user_id,
        "transaction_type": "top_up",
        "product": "Card",
        "status": random.choice(["completed", "pending"]),
        "currency": random.choice(CURRENCIES),
        "amount": round(random.uniform(50.00, 2000.00), 2),
        "metadata": metadata
    }


def generate_withdrawal_transaction(user_id: str, date: datetime) -> Dict[str, Any]:
    """Generates a withdrawal transaction."""
    bank_name = random.choice(["Chase", "Bank of America", "Wells Fargo", "Citibank"])
    account_last_four = f"{random.randint(1000, 9999):04d}"
    fee = round(random.uniform(0.00, 5.00), 2)
    
    return {
        "user_id": user_id,
        "transaction_type": "withdrawal",
        "product": "Card",
        "status": random.choice(["completed", "pending", "failed"]),
        "currency": random.choice(CURRENCIES),
        "amount": round(random.uniform(100.00, 5000.00), 2),
        "metadata": {
            "bank_name": bank_name,  # Always present for withdrawal
            "account_last_four": account_last_four,  # Always present for withdrawal
            "fee": fee  # Always present for withdrawal
        }
    }


def generate_bill_payment_transaction(user_id: str, date: datetime) -> Dict[str, Any]:
    """Generates a bill payment transaction."""
    bill_types = ["Electricity", "Water", "Internet", "Phone", "Gas", "Insurance"]
    bill_type = random.choice(bill_types)
    account_number = f"ACC{random.randint(100000, 999999)}"
    due_date = (date + timedelta(days=random.randint(1, 30))).isoformat()
    
    return {
        "user_id": user_id,
        "transaction_type": "bill_payment",
        "product": "Card",
        "status": random.choice(["completed", "pending", "failed"]),
        "currency": random.choice(CURRENCIES),
        "amount": round(random.uniform(20.00, 500.00), 2),
        "metadata": {
            "bill_type": bill_type,  # Always present for bill_payment
            "provider": f"{bill_type} Company",  # Always present for bill_payment
            "account_number": account_number,  # Always present for bill_payment
            "due_date": due_date  # Always present for bill_payment
        }
    }


def generate_earnings_transaction(user_id: str, date: datetime) -> Dict[str, Any]:
    """Generates an earnings transaction."""
    source = random.choice(["Freelance", "Salary", "Bonus", "Investment", "Referral"])
    period = f"{date.strftime('%Y-%m')}"
    tax_withheld = round(random.uniform(0.00, 100.00), 2)
    
    return {
        "user_id": user_id,
        "transaction_type": "earnings",
        "product": "Earnings",
        "status": "completed",  # Earnings are always completed
        "currency": random.choice(CURRENCIES),
        "amount": round(random.uniform(100.00, 5000.00), 2),
        "metadata": {
            "source": source,  # Always present for earnings
            "period": period,  # Always present for earnings
            "tax_withheld": tax_withheld  # Always present for earnings
        }
    }


def generate_transaction(user_id: str, date: datetime) -> Dict[str, Any]:
    """Generates a random transaction based on type."""
    transaction_type = random.choice(TRANSACTION_TYPES)
    
    generators = {
        "card": generate_card_transaction,
        "p2p": generate_p2p_transaction,
        "crypto": generate_crypto_transaction,
        "top_up": generate_top_up_transaction,
        "withdrawal": generate_withdrawal_transaction,
        "bill_payment": generate_bill_payment_transaction,
        "earnings": generate_earnings_transaction
    }
    
    return generators[transaction_type](user_id, date)


def create_transaction(transaction_data: Dict[str, Any]) -> bool:
    """Creates a transaction in the API."""
    try:
        response = requests.post(
            f"{BASE_URL}/transactions",
            json=transaction_data,
            timeout=5
        )
        if response.status_code == 201:
            return True
        else:
            print(f"Error creating transaction: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"Exception creating transaction: {e}")
        return False


def main():
    """Generates 1000 synthetic transactions."""
    print("🚀 Generating 1000 synthetic transactions...")
    print("-" * 60)
    
    # Use a test user_id
    user_id = "test_user_123"
    
    # Generate dates in the last 90 days
    base_date = datetime.now()
    dates = [base_date - timedelta(days=random.randint(0, 90)) for _ in range(1000)]
    dates.sort()  # Sort by date
    
    success_count = 0
    error_count = 0
    
    for i, date in enumerate(dates, 1):
        transaction = generate_transaction(user_id, date)
        
        if create_transaction(transaction):
            success_count += 1
            if i % 100 == 0:
                print(f"✅ Progress: {i}/1000 transactions created ({success_count} successful, {error_count} errors)")
        else:
            error_count += 1
        
        # Small pause to avoid overwhelming the API
        if i % 50 == 0:
            import time
            time.sleep(0.1)
    
    print("-" * 60)
    print(f"✅ Completed!")
    print(f"   Total: {success_count + error_count}")
    print(f"   Successful: {success_count}")
    print(f"   Errors: {error_count}")
    print(f"\n📊 Data generated for user_id: {user_id}")
    print(f"🔍 You can test the search with:")
    print(f"   curl \"http://localhost:8000/api/v1/transactions?user_id={user_id}\"")


if __name__ == "__main__":
    # Verify that the API is available
    max_retries = 30
    retry_count = 0
    
    print(f"🔍 Verifying connection to API at {BASE_URL}...")
    
    while retry_count < max_retries:
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=5)
            if response.status_code == 200:
                print("✅ API is available")
                print()
                main()
                break
            else:
                print(f"⚠️  API responded with status {response.status_code}, retrying...")
                retry_count += 1
        except requests.exceptions.ConnectionError:
            retry_count += 1
            if retry_count < max_retries:
                print(f"⏳ Waiting for API to be ready... ({retry_count}/{max_retries})")
                import time
                time.sleep(2)
            else:
                print("❌ Could not connect to API after several attempts")
                print(f"   URL attempted: {BASE_URL}")
                if "localhost" in BASE_URL or "127.0.0.1" in BASE_URL:
                    print("\n   To start the API locally:")
                    print("   docker-compose up api")
                    print("   or")
                    print("   uvicorn app.main:app --reload")
                else:
                    print("\n   Make sure the 'api' service is running:")
                    print("   docker-compose up -d api")
                break
        except Exception as e:
            print(f"❌ Error: {e}")
            break

